"""FastAPI application with audio upload, job queue, and status tracking."""

# Compatibility: SpeechBrain + huggingface_hub
# 1) SpeechBrain passes use_auth_token but huggingface_hub now expects token.
# 2) SpeechBrain expects optional custom.py 404 to be ValueError; hub raises RemoteEntryNotFoundError.
import huggingface_hub
from huggingface_hub.errors import RemoteEntryNotFoundError

_orig_hf_hub_download = huggingface_hub.hf_hub_download


def _hf_hub_download_compat(*args, **kwargs):
    if "use_auth_token" in kwargs:
        token = kwargs.pop("use_auth_token")
        if "token" not in kwargs:
            kwargs["token"] = token
    try:
        return _orig_hf_hub_download(*args, **kwargs)
    except RemoteEntryNotFoundError:
        if kwargs.get("filename") == "custom.py":
            raise ValueError("File not found on HF hub") from None
        raise


huggingface_hub.hf_hub_download = _hf_hub_download_compat

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
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from audio_utils import convert_to_wav, validate_audio_format
from job_queue import job_queue, process_worker
from extraction import format_backlink
from models import DecisionChartResponse, OutcomesResponse, PromoteResponse, SpeakerRenameRequest, SpeakerRoleUpdateRequest, StatusResponse, UploadResponse
from storage import create_job, delete_job, get_job, init_db, list_jobs, update_job

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


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
        n_ctx=4096,
        n_gpu_layers=n_gpu,
        chat_format="chatml",
        verbose=False,
    )
    logger.info("Phi-4-mini LLM loaded in %.1fs", time.perf_counter() - t2)

    # Start background worker
    worker_task = asyncio.create_task(process_worker(app.state))
    app.state.worker = worker_task

    # Re-queue incomplete jobs from previous run
    for job in list_jobs():
        if job["status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "stt"))
        elif job["extraction_status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "extract"))
        elif job.get("chart_status", "none") in ("pending", "processing"):
            await job_queue.put((job["id"], "chart"))

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
    duration_ms: float | None = None
    result = job.get("result")
    if isinstance(result, dict) and result.get("duration"):
        duration_ms = result["duration"] * 1000

    return StatusResponse(
        status=job["status"],
        extraction_status=job.get("extraction_status", "none"),
        chart_status=job.get("chart_status", "none"),
        duration_ms=duration_ms,
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


@app.get("/recordings/{job_id}/summary")
async def get_recording_summary(job_id: str, request: Request):
    """Return AI-generated meeting summary. Cached after first generation."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    summary = job.get("summary")
    if summary is not None:
        return summary

    from summary import run_summary

    app_state = request.app.state
    summary = await asyncio.to_thread(run_summary, job_id, app_state)
    update_job(job_id, summary=summary)
    return summary


@app.get("/recordings/{job_id}/audio")
async def get_recording_audio(job_id: str):
    """Stream the WAV audio file for a recording."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    file_path = job["file_path"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        file_path,
        media_type="audio/wav",
        headers={"Accept-Ranges": "bytes"},
    )


@app.patch("/recordings/{job_id}/speakers")
async def rename_speakers(job_id: str, body: SpeakerRenameRequest):
    """Rename speaker labels in the transcript.

    Accepts a mapping of old label -> new label. Updates all matching labels
    in both segments and speakers arrays of the stored transcript result.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No transcript found")

    renames = body.renames

    # Update speaker labels in segments
    for seg in result.get("segments", []):
        if seg.get("speaker") in renames:
            seg["speaker"] = renames[seg["speaker"]]

    # Update speaker labels in speakers stats
    for spk in result.get("speakers", []):
        if spk.get("label") in renames:
            spk["label"] = renames[spk["label"]]

    update_job(job_id, result=result)
    return result


@app.patch("/recordings/{job_id}/speakers/roles")
async def update_speaker_roles(job_id: str, body: SpeakerRoleUpdateRequest):
    """Update the inferred role for one or more speakers.

    Accepts a mapping of speaker label -> role string and persists it back
    into the result.speakers[].role field of the stored transcript.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No transcript found")

    for spk in result.get("speakers", []):
        label = spk.get("label", "")
        if label in body.roles:
            spk["role"] = body.roles[label].strip()

    update_job(job_id, result=result)
    return result


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


@app.get(
    "/recordings/{job_id}/chart", response_model=DecisionChartResponse
)
async def get_recording_chart(job_id: str):
    """Return the decision chart status and PlantUML text."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return DecisionChartResponse(
        job_id=job_id,
        chart_status=job.get("chart_status", "none"),
        chart_plantuml=job.get("chart_plantuml"),
    )


@app.post("/recordings/{job_id}/chart", status_code=202)
async def trigger_chart_generation(job_id: str):
    """Manually trigger chart generation. Returns 409 if already in progress/completed."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("extraction_status", "none") != "completed":
        raise HTTPException(
            status_code=400, detail="Extraction must be completed before generating a chart"
        )
    if job.get("chart_status", "none") in ("pending", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Chart generation is already in progress for this recording",
        )
    # Reset previous result so regeneration is treated as a fresh run
    update_job(job_id, chart_status="pending", chart_plantuml=None, chart_error=None)
    await job_queue.put((job_id, "chart"))
    return {"message": "Chart generation enqueued", "job_id": job_id}


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
        id=promoted_id,
        type=promote_type,
        backlink=backlink,
        title=outcome.get("title", ""),
        detail=outcome.get("detail", ""),
    )


@app.post("/recordings/{job_id}/documents", status_code=201)
async def upload_document(job_id: str, file: UploadFile = File(...)):
    """Upload a PDF or PPTX slide deck, parse it, and store it on the job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    filename = file.filename or "document"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".pptx", ".ppt"):
        raise HTTPException(status_code=400, detail="Only .pdf and .pptx files are supported")

    # Save temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        from document_parsing import parse_document
        doc = parse_document(tmp_path)
        doc["filename"] = filename
    finally:
        os.unlink(tmp_path)

    documents = job.get("documents", []) or []
    documents.append(doc)
    update_job(job_id, documents=documents)
    return {"doc_index": len(documents) - 1, "filename": filename, "slide_count": len(doc["slides"])}


@app.get("/recordings/{job_id}/documents")
async def get_documents(job_id: str):
    """Return all parsed documents for a recording."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    documents = job.get("documents", []) or []
    return [{"doc_index": i, "filename": d.get("filename"), "type": d.get("type"), "slide_count": len(d.get("slides", []))} for i, d in enumerate(documents)]


@app.get("/recordings/{job_id}/documents/{doc_index}")
async def get_document_detail(job_id: str, doc_index: int):
    """Return the parsed slides for a specific document."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    documents = job.get("documents", []) or []
    if doc_index >= len(documents):
        raise HTTPException(status_code=404, detail="Document not found")
    return documents[doc_index]


@app.get("/recordings/{job_id}/alignment/{doc_index}")
async def get_alignment(job_id: str, doc_index: int):
    """Return LLM-generated alignment between document slides and transcript."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    from alignment import run_alignment
    alignments = await asyncio.to_thread(run_alignment, job_id, doc_index, app.state)
    return {"alignments": alignments}


@app.post("/recordings/{job_id}/generate-plan")
async def generate_plan(job_id: str, request: Request):
    """Generate a structured project plan from meeting outcomes using the LLM."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready yet")

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    project_goal = body.get("projectGoal") if isinstance(body, dict) else None

    from plan_generation import run_plan_generation
    plan = await asyncio.to_thread(run_plan_generation, job_id, project_goal, app.state)
    return plan


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
