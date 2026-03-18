"""FastAPI application with audio upload, job queue, and status tracking."""

import asyncio
import logging
import os
import subprocess
import time
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import aiofiles
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from audio_utils import convert_to_wav, validate_audio_format
from job_queue import job_queue, process_worker
from extraction import format_backlink
from models import (
    AttachmentResponse,
    AttachmentTextResponse,
    OutcomesResponse,
    PromoteResponse,
    StatusResponse,
    UploadResponse,
)
from storage import (
    create_attachment,
    create_job,
    delete_attachment,
    delete_job,
    get_attachment,
    get_job,
    init_db,
    list_attachments,
    list_jobs,
    update_job,
)
from text_extraction import extract_text

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


def _migrate_speaker_stats():
    """Recompute speaker stats for old jobs missing extended fields (talk_time, wpm, etc.)."""
    from transcription import calculate_speaker_stats

    migrated = 0
    for job in list_jobs():
        if job["status"] != "completed" or not job.get("result"):
            continue
        result = job["result"]
        speakers = result.get("speakers", [])
        if not speakers or "talk_time" in speakers[0]:
            continue  # Already has extended stats

        segments = result.get("segments", [])
        duration = result.get("duration", 0)
        if not segments:
            continue

        new_stats = calculate_speaker_stats(segments, duration)
        result["speakers"] = new_stats
        # Also add processing_time if missing
        if "processing_time" not in result:
            result["processing_time"] = 0
        update_job(job["id"], result=result)
        migrated += 1

    if migrated:
        logger.info("Migrated speaker stats for %d old job(s)", migrated)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: load ML models at startup, cleanup on shutdown."""
    # Startup
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    init_db()

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

    # Load Phi-4-mini LLM for extraction
    t2 = time.perf_counter()
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    llm_model_path = os.environ.get("LLM_MODEL_PATH")
    if not llm_model_path:
        # Auto-download Q4_K_M quantization of Phi-4-mini-instruct
        llm_model_path = hf_hub_download(
            repo_id="unsloth/Phi-4-mini-instruct-GGUF",
            filename="Phi-4-mini-instruct-Q4_K_M.gguf",
            token=os.environ.get("HF_TOKEN"),
        )
        logger.info("Downloaded Phi-4-mini model to %s", llm_model_path)

    n_gpu = -1 if os.environ.get("LLM_GPU", "1") != "0" else 0
    app.state.llm = Llama(
        model_path=llm_model_path,
        n_ctx=8192,  # Bumped from 4096 for Phase 8 document context injection
        n_gpu_layers=n_gpu,
        chat_format="chatml",
        verbose=False,
    )
    logger.info("Phi-4-mini LLM loaded in %.1fs", time.perf_counter() - t2)

    # Migrate old job results: recompute speaker stats for records missing extended fields
    _migrate_speaker_stats()

    # Start background worker
    worker_task = asyncio.create_task(process_worker(app.state))
    app.state.worker = worker_task

    # Re-queue incomplete jobs from previous run
    for job in list_jobs():
        if job["status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "stt"))
        elif job["extraction_status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "extract"))

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


@app.get("/recordings/{job_id}/audio")
async def get_recording_audio(job_id: str):
    """Return the WAV audio file for a completed recording."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    wav_path = job["file_path"]
    if not os.path.exists(wav_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        wav_path,
        media_type="audio/wav",
        headers={"Accept-Ranges": "bytes"},
    )


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
    if job.get("extraction_status", "none") not in ("none", "failed"):
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


@app.post("/recordings/{job_id}/generate-prd")
async def generate_prd_endpoint(job_id: str):
    """Generate a PRD from a recording's extracted outcomes."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise HTTPException(status_code=400, detail="No outcomes to generate from")

    from document_generation import generate_prd

    content = await asyncio.to_thread(generate_prd, job_id, app.state)
    return {
        "content": content,
        "title": f"PRD - {job.get('original_filename', 'Recording')}",
    }


@app.post("/recordings/{job_id}/generate-diagram")
async def generate_diagram_endpoint(job_id: str):
    """Generate a Mermaid diagram from a recording's extracted outcomes.

    Automatically selects the best diagram type (user_flow or erd) based on content.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise HTTPException(status_code=400, detail="No outcomes to generate from")

    from document_generation import generate_diagram

    content, diagram_type = await asyncio.to_thread(generate_diagram, job_id, app.state)
    type_label = "User Flow" if diagram_type == "user_flow" else "ERD"
    return {
        "content": content,
        "type": diagram_type,
        "title": f"{type_label} - {job.get('original_filename', 'Recording')}",
    }


@app.patch("/recordings/{job_id}/speakers/{speaker_label}")
async def update_speaker(job_id: str, speaker_label: str, request: Request):
    """Update a speaker's custom label or role."""
    decoded_label = urllib.parse.unquote(speaker_label)
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    body = await request.json()
    result = job["result"]
    speakers = result.get("speakers", [])

    matched = False
    for speaker in speakers:
        if speaker["label"] == decoded_label:
            if "custom_label" in body:
                speaker["custom_label"] = body["custom_label"]
            if "role" in body:
                speaker["role"] = body["role"]
            matched = True
            break

    if not matched:
        raise HTTPException(status_code=404, detail="Speaker not found")

    update_job(job_id, result=result)
    return {"ok": True}


@app.delete("/recordings/{job_id}", status_code=204)
async def delete_recording(job_id: str):
    """Delete a recording and its associated files."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Clean up files
    file_path = job.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    # Clean up original upload (pattern: {job_id}_{filename})
    for f in os.listdir(UPLOADS_DIR):
        if f.startswith(job_id):
            path = os.path.join(UPLOADS_DIR, f)
            if os.path.exists(path):
                os.remove(path)

    delete_job(job_id)
    return None


# --- Attachment endpoints ---

ALLOWED_ATTACHMENT_TYPES = {"pdf", "docx", "txt"}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post(
    "/recordings/{job_id}/attachments",
    status_code=201,
    response_model=AttachmentResponse,
)
async def upload_attachment(job_id: str, file: UploadFile = File(...)):
    """Upload a document attachment for a recording."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Determine file type from extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Accepted: pdf, docx, txt",
        )

    # Read file content and check size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB",
        )

    # Save file to UPLOADS_DIR/{job_id}/
    attachment_dir = os.path.join(UPLOADS_DIR, job_id)
    os.makedirs(attachment_dir, exist_ok=True)
    saved_path = os.path.join(attachment_dir, file.filename)
    async with aiofiles.open(saved_path, "wb") as f:
        await f.write(file_bytes)

    # Extract text
    text, extraction_error = extract_text(saved_path, ext)

    # Store in DB
    attachment_id = str(uuid4())
    record = create_attachment(
        attachment_id=attachment_id,
        recording_id=job_id,
        filename=file.filename,
        file_type=ext,
        file_size=len(file_bytes),
        extracted_text=text,
        extraction_error=extraction_error,
    )
    return AttachmentResponse(**record)


@app.get(
    "/recordings/{job_id}/attachments",
    response_model=list[AttachmentResponse],
)
async def list_recording_attachments(job_id: str):
    """List all attachments for a recording (metadata only, no extracted text)."""
    return list_attachments(job_id)


@app.delete(
    "/recordings/{job_id}/attachments/{attachment_id}",
    status_code=204,
)
async def delete_recording_attachment(job_id: str, attachment_id: str):
    """Delete an attachment record and its file."""
    record = get_attachment(attachment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    delete_attachment(attachment_id)

    # Best-effort delete file from disk
    try:
        file_path = os.path.join(UPLOADS_DIR, job_id, record["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        logger.warning("Failed to delete attachment file for %s", attachment_id)

    return None


@app.get(
    "/recordings/{job_id}/attachments/{attachment_id}/text",
    response_model=AttachmentTextResponse,
)
async def get_attachment_text(job_id: str, attachment_id: str):
    """Return the extracted text for an attachment."""
    record = get_attachment(attachment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return AttachmentTextResponse(
        id=record["id"],
        extracted_text=record["extracted_text"],
    )
