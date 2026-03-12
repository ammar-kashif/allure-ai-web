"""FastAPI application with audio upload, job queue, and status tracking."""

import asyncio
import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from audio_utils import convert_to_wav, validate_audio_format
from job_queue import job_queue, process_worker
from extraction import format_backlink
from models import OutcomesResponse, PromoteResponse, StatusResponse, UploadResponse
from storage import create_job, get_job, update_job

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: load ML models at startup, cleanup on shutdown."""
    # Startup
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Load Moonshine Voice transcriber
    t0 = time.perf_counter()
    from moonshine_voice import Transcriber, get_model_for_language

    model_path, model_arch = get_model_for_language("en")
    app.state.transcriber = Transcriber(
        model_path=model_path,
        model_arch=model_arch,
    )
    logger.info("Moonshine transcriber loaded in %.1fs", time.perf_counter() - t0)

    # Load SpeechBrain ECAPA-TDNN for speaker diarization
    t1 = time.perf_counter()
    from speechbrain.inference.speaker import EncoderClassifier

    from transcription import FastDiarizer

    encoder = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
    )
    app.state.diarizer = FastDiarizer(encoder=encoder)
    logger.info("SpeechBrain ECAPA-TDNN diarizer loaded in %.1fs", time.perf_counter() - t1)

    # Start background worker
    worker_task = asyncio.create_task(process_worker(app.state))
    app.state.worker = worker_task
    yield
    # Shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Allure AI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/recordings", status_code=201, response_model=UploadResponse)
async def upload_recording(file: UploadFile = File(...)):
    """Accept audio file upload and return job ID."""
    if not file.filename or not validate_audio_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Accepted: webm, mp3, wav, m4a, mp4",
        )

    job_id = str(uuid4())

    # Read file bytes before responding
    file_bytes = await file.read()

    # Save uploaded file
    original_path = os.path.join(UPLOADS_DIR, f"{job_id}_{file.filename}")
    async with aiofiles.open(original_path, "wb") as f:
        await f.write(file_bytes)

    # Convert to 16kHz mono WAV
    wav_path = os.path.join(UPLOADS_DIR, f"{job_id}.wav")
    try:
        convert_to_wav(original_path, wav_path)
    except subprocess.CalledProcessError:
        # Clean up original file on conversion failure
        if os.path.exists(original_path):
            os.remove(original_path)
        raise HTTPException(
            status_code=422,
            detail="Audio conversion failed",
        )

    # Create job and enqueue
    create_job(job_id, wav_path, file.filename)
    await job_queue.put((job_id, "stt"))

    return UploadResponse(id=job_id)


@app.get("/recordings/{job_id}/status", response_model=StatusResponse)
async def get_recording_status(job_id: str):
    """Return current job status."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(
        status=job["status"],
        extraction_status=job.get("extraction_status", "none"),
    )


@app.get("/recordings/{job_id}/transcript")
async def get_recording_transcript(job_id: str):
    """Return transcript for completed job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")
    return job["result"]


@app.get(
    "/recordings/{job_id}/outcomes", response_model=OutcomesResponse
)
async def get_recording_outcomes(job_id: str):
    """Return extraction outcomes for a recording."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return OutcomesResponse(
        job_id=job_id,
        extraction_status=job.get("extraction_status", "none"),
        outcomes=job.get("outcomes", []),
    )


@app.post("/recordings/{job_id}/extract", status_code=202)
async def trigger_extraction(job_id: str):
    """Manually trigger extraction. One-shot: returns 409 if already triggered."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400, detail="Transcript not ready for extraction"
        )
    if job.get("extraction_status", "none") != "none":
        raise HTTPException(
            status_code=409,
            detail="Extraction already triggered or completed for this recording",
        )
    update_job(job_id, extraction_status="pending")
    await job_queue.put((job_id, "extract"))
    return {"message": "Extraction enqueued", "job_id": job_id}


@app.post(
    "/recordings/{job_id}/outcomes/{outcome_index}/promote",
    response_model=PromoteResponse,
)
async def promote_outcome(job_id: str, outcome_index: int):
    """Promote an outcome to a task or requirement."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    outcomes = job.get("outcomes", [])
    if outcome_index < 0 or outcome_index >= len(outcomes):
        raise HTTPException(status_code=404, detail="Outcome not found")

    outcome = outcomes[outcome_index]

    # Only action_items and requirements can be promoted
    if outcome["type"] not in ("action_item", "requirement"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot promote outcome of type '{outcome['type']}'. Only action_item and requirement can be promoted.",
        )

    if outcome.get("promoted", False):
        raise HTTPException(
            status_code=409, detail="Outcome already promoted"
        )

    # Generate promoted item
    from uuid import uuid4

    promoted_id = str(uuid4())
    outcome["promoted"] = True
    outcome["promoted_id"] = promoted_id

    # Build backlink from first evidence ref
    evidence_refs = outcome.get("evidence_refs", [])
    if evidence_refs:
        ref = evidence_refs[0]
        backlink = format_backlink(
            job.get("original_filename", "Recording"),
            ref.get("timestamp", 0.0),
            ref.get("speaker", "Unknown"),
        )
    else:
        backlink = format_backlink(
            job.get("original_filename", "Recording"), 0.0, "Unknown"
        )

    # Map type
    promote_type = (
        "task" if outcome["type"] == "action_item" else "requirement"
    )

    # Persist changes
    update_job(job_id, outcomes=outcomes)

    return PromoteResponse(
        id=promoted_id, type=promote_type, backlink=backlink
    )
