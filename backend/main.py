"""FastAPI application with audio upload, job queue, and status tracking."""

import asyncio
import logging
import os
import subprocess
import time
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Surface app-level INFO logs under uvicorn (it only routes uvicorn.* by default).
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    force=True,
)

import aiofiles
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from audio_utils import convert_to_wav, detect_no_audio_track, validate_audio_format
from job_queue import job_queue, process_worker, start_chunk_worker_pool
from extraction import format_backlink
from observability import log_event, step_timer
from meeting_bot import dispatch_store
from meeting_bot.router import router as meeting_bot_router
import projects_store
import segments_store
from entities import store as entities_store
from ghost import (
    conversations as ghost_convos,
    embeddings as ghost_embeddings,
    settings as ghost_settings,
)
from ghost.eval import store as ghost_eval_store
from streaming import progress_store as streaming_progress_store
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


def _backfill_meeting_metadata():
    """One-time backfill: for completed jobs whose result has empty
    meeting_title/description (because they were extracted before the
    fallback shipped, OR because the LLM returned empty on a short
    recording), synthesize a non-empty title/description from segments
    using the same fallback helpers run_extraction uses.

    No LLM calls — purely deterministic from existing transcript text.
    """
    from extraction import (
        _fallback_title_from_segments,
        _fallback_description_from_segments,
    )

    backfilled = 0
    for job in list_jobs():
        if job["status"] != "completed" or not job.get("result"):
            continue
        result = job["result"]
        segments = result.get("segments", [])
        if not segments:
            continue

        title = (result.get("meeting_title") or "").strip()
        desc = (result.get("meeting_description") or "").strip()
        if title and desc:
            continue

        updated = False
        if not title:
            result["meeting_title"] = _fallback_title_from_segments(segments)
            updated = True
        if not desc:
            result["meeting_description"] = _fallback_description_from_segments(segments)
            updated = True

        if updated:
            update_job(job["id"], result=result)
            backfilled += 1

    if backfilled:
        logger.info(
            "Backfilled meeting_title/description for %d job(s) using "
            "transcript-derived fallback (no LLM call).",
            backfilled,
        )


def _sync_all_metadata_to_frontend():
    """Push meeting_title + meeting_description for every completed job
    into the frontend's SQLite recordings row. Idempotent — running it on
    every startup is safe; rows that already match get a no-op write that
    just clears the cached transcript blob."""
    from frontend_sync import push_metadata_to_frontend

    synced = 0
    for job in list_jobs():
        if job["status"] != "completed" or not job.get("result"):
            continue
        result = job["result"]
        title = (result.get("meeting_title") or "").strip()
        desc = (result.get("meeting_description") or "").strip()
        if not (title or desc):
            continue
        out = push_metadata_to_frontend(job["id"], title=title, description=desc)
        if out.get("title_updated") or out.get("description_updated"):
            synced += 1
    if synced:
        logger.info(
            "Synced title/description to frontend DB for %d recording(s).",
            synced,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: load ML models at startup, cleanup on shutdown."""
    # Startup
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    init_db()
    dispatch_store.init()
    # Phase 1 foundation: project model, segments mirror, streaming progress.
    # Order matters: projects_store backfills from dispatches, so dispatch_store
    # must be initialised first.
    projects_store.init()
    segments_store.init()
    entities_store.init()
    ghost_embeddings.init()
    ghost_settings.init()
    ghost_convos.init()
    ghost_eval_store.init()
    streaming_progress_store.init()

    # Load Moonshine Voice transcriber
    t0 = time.perf_counter()
    from moonshine_voice import Transcriber, get_model_for_language

    model_path, model_arch = get_model_for_language("en")
    app.state.transcriber = Transcriber(
        model_path=model_path,
        model_arch=model_arch,
    )
    logger.info("Moonshine transcriber loaded in %.1fs", time.perf_counter() - t0)

    # Load SpeechBrain ECAPA-TDNN + silero-vad for speaker diarization
    t1 = time.perf_counter()
    from speechbrain.inference.speaker import EncoderClassifier
    from silero_vad import load_silero_vad

    from transcription import FastDiarizer

    encoder = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
    )
    vad_model = load_silero_vad(onnx=False)
    app.state.diarizer = FastDiarizer(
        encoder=encoder,
        vad_model=vad_model,
        window_size=float(os.environ.get("DIARIZER_WINDOW_SECONDS", "2.0")),
        hop_size=float(os.environ.get("DIARIZER_HOP_SECONDS", "0.75")),
        clustering_method=os.environ.get("DIARIZER_CLUSTERING_METHOD", "spectral"),
        distance_threshold=float(
            os.environ.get("DIARIZER_DISTANCE_THRESHOLD", "0.75")
        ),
        linkage=os.environ.get("DIARIZER_LINKAGE", "average"),
        vad_threshold=float(os.environ.get("DIARIZER_VAD_THRESHOLD", "0.5")),
        min_speech_duration=float(
            os.environ.get("DIARIZER_MIN_SPEECH_SECONDS", "0.5")
        ),
        centroid_merge_threshold=float(
            os.environ.get("DIARIZER_CENTROID_MERGE_THRESHOLD", "0.0")
        ),
        max_speakers=int(os.environ.get("DIARIZER_MAX_SPEAKERS", "6")),
        min_windows_for_spectral=int(
            os.environ.get("DIARIZER_MIN_WINDOWS_FOR_SPECTRAL", "10")
        ),
    )
    logger.info(
        "silero-vad + SpeechBrain ECAPA-TDNN diarizer loaded in %.1fs",
        time.perf_counter() - t1,
    )

    # Load punctuation + capitalization model
    t_punct = time.perf_counter()
    from deepmultilingualpunctuation import PunctuationModel

    punct_model_id = os.environ.get(
        "PUNCTUATION_MODEL", "oliverguhr/fullstop-punctuation-multilang-large"
    )
    try:
        app.state.punctuator = PunctuationModel(model=punct_model_id)
        logger.info(
            "Punctuation model '%s' loaded in %.1fs",
            punct_model_id,
            time.perf_counter() - t_punct,
        )
    except Exception as exc:
        logger.warning(
            "Punctuation model failed to load (%s); transcripts will stay unpunctuated",
            exc,
        )
        app.state.punctuator = None

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
        n_ctx=16384,
        n_gpu_layers=n_gpu,
        chat_format="chatml",
        verbose=False,
    )
    logger.info("Phi-4-mini LLM loaded in %.1fs", time.perf_counter() - t2)

    # Phase 1: mirror existing jobs.result.segments into the segments
    # table. Idempotent -- safe to run on every startup.
    try:
        n = segments_store.backfill_all_from_jobs()
        if n:
            logger.info("Backfilled segments table for %d recording(s)", n)
    except Exception:
        logger.exception("segments backfill failed")

    # Phase 3 backfill: populate outcomes_fts for legacy recordings whose
    # extract ran before the entitize chain existed. Without this,
    # search_outcomes silently returns [] for older data. Idempotent
    # (deletes + re-inserts per recording).
    try:
        n = entities_store.backfill_outcomes_fts_all()
        if n:
            logger.info("Backfilled outcomes_fts for %d recording(s)", n)
    except Exception:
        logger.exception("outcomes_fts backfill failed")

    # Phase 1+3 interaction: when segments are mirrored before the FTS
    # triggers exist (first deploy after upgrade), segments_fts is empty.
    # The triggers now exist; re-run the segments mirror so trigger-based
    # FTS inserts fire. Idempotent.
    try:
        n2 = segments_store.backfill_all_from_jobs()
        if n2:
            logger.info("Re-mirrored segments to fire FTS triggers for %d recording(s)", n2)
    except Exception:
        logger.exception("post-FTS segments re-mirror failed")

    # Migrate old job results: recompute speaker stats for records missing extended fields
    _migrate_speaker_stats()

    # One-time backfill: fill empty meeting_title/description from segments
    # (handles jobs extracted before the title fallback shipped).
    _backfill_meeting_metadata()

    # Push all known titles/descriptions from backend → frontend SQLite.
    # Catches anything the polling-based sync missed.
    _sync_all_metadata_to_frontend()

    # Start background worker
    worker_task = asyncio.create_task(process_worker(app.state))
    app.state.worker = worker_task

    # Start chunk worker pool (streaming pipeline)
    app.state.chunk_workers = start_chunk_worker_pool(app.state)
    logger.info("Started %d chunk worker(s)", len(app.state.chunk_workers))

    # Re-queue incomplete jobs from previous run
    for job in list_jobs():
        if job["status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "stt"))
        elif job["extraction_status"] in ("pending", "processing"):
            await job_queue.put((job["id"], "extract"))

    # Resume streaming pipeline: re-enqueue any chunks that were mid-flight
    # or unprocessed at shutdown, and trigger finalize for recordings that
    # had completed all chunks but not yet finalized.
    try:
        from streaming.resume import resume_unfinished
        from meeting_bot.config import MEETING_BOT_RECORDINGS_DIR
        from job_queue import chunk_queue

        actions = resume_unfinished(MEETING_BOT_RECORDINGS_DIR)
        for action in actions:
            if action["action"] == "enqueue_chunk":
                offset = float((action["chunk_seq"] - 1) * 30)
                await chunk_queue.put((
                    action["recording_id"],
                    action["chunk_seq"],
                    action["chunk_path"],
                    action["pipeline_version"],
                    offset,
                ))
            elif action["action"] == "enqueue_finalize":
                await job_queue.put((action["recording_id"], "finalize"))
    except Exception:
        logger.exception("streaming resume on startup failed")

    # Start meeting-bot filesystem watcher
    from meeting_bot.watcher import run_watcher

    app.state.bot_watcher = run_watcher(app.state)

    yield
    # Shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    for w in getattr(app.state, "chunk_workers", []) or []:
        w.cancel()
        try:
            await w
        except asyncio.CancelledError:
            pass
    if getattr(app.state, "bot_watcher_stop", None):
        app.state.bot_watcher_stop.set()
    if getattr(app.state, "bot_watcher", None):
        try:
            await asyncio.wait_for(app.state.bot_watcher, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            app.state.bot_watcher.cancel()


app = FastAPI(title="Allure AI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(meeting_bot_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/logs")
async def list_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    category: str | None = None,
    status: str | None = None,
    recording_id: str | None = None,
    job_id: str | None = None,
    dispatch_id: str | None = None,
):
    """Return newest persisted operational events."""
    from log_store import list_events

    return list_events(
        limit=limit,
        category=category,
        status=status,
        recording_id=recording_id,
        job_id=job_id,
        dispatch_id=dispatch_id,
    )


@app.get("/metrics")
async def get_metrics(
    window_hours: int = Query(default=24, ge=1, le=720),
    category: str | None = None,
):
    """Per-step latency rollup from the logs table.

    Window is anchored to "now"; default is the trailing 24h. CI / Phase 7
    eval jobs hit this endpoint to enforce p95 thresholds.
    """
    from datetime import datetime, timedelta, timezone

    from metrics import pipeline_summary

    since = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )
    return pipeline_summary(since_iso=since) | {"window_hours": window_hours}


# --- Projects ---


@app.get("/projects")
async def list_projects(include_archived: bool = False):
    """List active projects (or all, if include_archived=true)."""
    if include_archived:
        return projects_store.list_all()
    return projects_store.list_active()


@app.post("/projects", status_code=201)
async def create_project(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    description = body.get("description") or ""
    return projects_store.create(name=name, description=description)


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    project = projects_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch("/projects/{project_id}")
async def update_project(project_id: str, request: Request):
    body = await request.json()
    allowed = {"name", "description"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="No updatable fields provided")
    try:
        return projects_store.update(project_id, **fields)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/projects/{project_id}/archive", status_code=200)
async def archive_project(project_id: str):
    try:
        return projects_store.archive(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


# --- Entities (Ghost retrieval substrate) ---


@app.get("/entities")
async def list_entities_endpoint(kind: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    return entities_store.list_entities(kind=kind, limit=limit)


@app.get("/entities/{entity_id}")
async def get_entity_endpoint(entity_id: str):
    entity = entities_store.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@app.get("/entities/{entity_id}/mentions")
async def list_entity_mentions(
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    source_types: str | None = None,
):
    if entities_store.get_entity(entity_id) is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    sts = [s.strip() for s in source_types.split(",")] if source_types else None
    return entities_store.list_mentions(entity_id, source_types=sts, limit=limit)


@app.get("/entities/{entity_id}/activity")
async def entity_recent_activity(
    entity_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    if entities_store.get_entity(entity_id) is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entities_store.list_recent_activity_by_entity(entity_id, limit=limit)


@app.post("/recordings/{job_id}/entitize", status_code=202)
async def trigger_entitize(job_id: str):
    """Manually re-run entity extraction for a recording. Idempotent."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")
    await job_queue.put((job_id, "entitize"))
    return {"job_id": job_id, "queued": True}


# --- Ghost retrieval (raw search, no agent yet) ---


@app.post("/ghost/search")
async def ghost_search(request: Request):
    """Hybrid retrieval. Body: { query, scope?: {recording_ids?, project_ids?,
    since_iso?, until_iso?}, kinds?: ["transcripts","attachments","outcomes"],
    k?: 8 }.

    Returns results per kind. Used by the agent's tools; also useful as a
    direct API for debugging and the eventual frontend.
    """
    from ghost.retrieval import HybridRetriever, Scope

    body = await request.json()
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    scope_dict = body.get("scope") or {}
    scope = Scope(
        recording_ids=scope_dict.get("recording_ids"),
        project_ids=scope_dict.get("project_ids"),
        since_iso=scope_dict.get("since_iso"),
        until_iso=scope_dict.get("until_iso"),
    )
    kinds = set(body.get("kinds") or ["transcripts", "attachments", "outcomes"])
    k = int(body.get("k") or 8)
    h = HybridRetriever()
    out: dict[str, Any] = {}
    if "transcripts" in kinds:
        out["transcripts"] = h.search_transcripts(query, scope=scope, k=k)
    if "attachments" in kinds:
        out["attachments"] = h.search_attachments(query, scope=scope, k=k)
    if "outcomes" in kinds:
        out["outcomes"] = h.search_outcomes(query, scope=scope, k=k)
    return out


# --- Ghost agent + settings ---


@app.get("/ghost/settings")
async def get_ghost_settings():
    return ghost_settings.get()


@app.patch("/ghost/settings")
async def update_ghost_settings(request: Request):
    body = await request.json()
    try:
        return ghost_settings.update(
            mode=body.get("mode"),
            provider=body.get("provider"),
            api_key=body.get("api_key"),
            model=body.get("model"),
            monthly_cap_usd=body.get("monthly_cap_usd"),
            base_url=body.get("base_url"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/ghost/ask")
async def ghost_ask(request: Request):
    """Ask Ghost a question. Body: { question, conv_id?, project_id?,
    scope_hint?: 'single_recording' | 'single_project' | 'cross_project' }.
    """
    from ghost.agent import ask as ghost_ask_fn

    body = await request.json()
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        return await asyncio.to_thread(
            ghost_ask_fn,
            question,
            conv_id=body.get("conv_id"),
            project_id=body.get("project_id"),
            scope_hint=body.get("scope_hint") or "cross_project",
        )
    except RuntimeError as exc:
        # Settings issues, monthly cap, etc.
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/ghost/ask/stream")
async def ghost_ask_stream(request: Request):
    """SSE stream of agent activity + final answer.

    Each event payload is JSON; one event per line. Kinds:
        triage              {intent, scope, can_spawn_subagents}
        tool.start          {name, arguments}
        tool.done           {name, summary, error?}
        subagent.spawning   {task_count, questions}
        subagent.started    {question}
        subagent.done       {question, error?}
        final               {conv_id, answer, citations, cost_usd, ...}
        error               {message}

    The agent runs in a worker thread; events are pushed onto a
    thread-safe queue that the SSE generator drains.
    """
    import json as _json
    import queue as _queue
    import threading

    from fastapi.responses import StreamingResponse

    from ghost.agent import ask as ghost_ask_fn

    body = await request.json()
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    conv_id = body.get("conv_id")
    project_id = body.get("project_id")
    scope_hint = body.get("scope_hint") or "cross_project"

    q: "_queue.Queue[dict]" = _queue.Queue()
    SENTINEL = {"__sentinel__": True}

    def emit(event: dict):
        q.put(event)

    def runner():
        try:
            ghost_ask_fn(
                question,
                conv_id=conv_id,
                project_id=project_id,
                scope_hint=scope_hint,
                on_event=emit,
            )
        except Exception as exc:
            emit({"kind": "error", "message": str(exc)})
        finally:
            emit(SENTINEL)

    threading.Thread(target=runner, daemon=True).start()

    async def gen():
        while True:
            try:
                event = await asyncio.wait_for(
                    asyncio.to_thread(q.get, True, 30),
                    timeout=35,
                )
            except (asyncio.TimeoutError, _queue.Empty):
                yield "data: " + _json.dumps({"kind": "heartbeat"}) + "\n\n"
                continue
            if event.get("__sentinel__"):
                return
            yield "data: " + _json.dumps(event, default=str) + "\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/ghost/conversations")
async def list_ghost_conversations(limit: int = Query(default=50, ge=1, le=200)):
    return ghost_convos.list_conversations(limit=limit)


@app.get("/ghost/conversations/{conv_id}")
async def get_ghost_conversation(conv_id: str):
    conv = ghost_convos.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv["messages"] = ghost_convos.list_messages(conv_id)
    return conv


@app.delete("/ghost/conversations/{conv_id}", status_code=204)
async def delete_ghost_conversation(conv_id: str):
    if not ghost_convos.delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/ghost/cost")
async def ghost_cost():
    """Month-to-date Ghost spend + the configured monthly cap."""
    settings = ghost_settings.get()
    return {
        "month_to_date_usd": ghost_convos.month_to_date_cost_usd(),
        "monthly_cap_usd": settings.get("monthly_cap_usd") or 0.0,
    }


# --- Ghost eval (synthetic queries + nightly runner stats) ---


@app.post("/ghost/eval/generate")
async def ghost_eval_generate(n_target: int = Query(default=50, ge=1, le=500)):
    from ghost.eval.generator import generate
    return await asyncio.to_thread(generate, n_target)


@app.get("/ghost/eval/queries")
async def ghost_eval_queries(limit: int = Query(default=200, ge=1, le=1000)):
    return ghost_eval_store.list_queries(limit=limit)


@app.post("/ghost/eval/run", status_code=202)
async def ghost_eval_run(limit: int = Query(default=100, ge=1, le=500)):
    from ghost.eval.runner import run_all
    return await asyncio.to_thread(run_all, limit)


@app.get("/ghost/eval/stats")
async def ghost_eval_stats(window_hours: int = Query(default=24 * 7, ge=1, le=24 * 90)):
    return ghost_eval_store.stats(window_hours=window_hours)


@app.get("/ghost/eval/runs")
async def ghost_eval_runs(
    query_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    return ghost_eval_store.list_runs(query_id=query_id, limit=limit)


@app.post("/recordings", status_code=201, response_model=UploadResponse)
async def upload_recording(file: UploadFile = File(...)):
    """Accept audio file upload and return job ID."""
    if not file.filename or not validate_audio_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Accepted: webm, mp3, wav, m4a, mp4, mov",
        )

    job_id = str(uuid4())

    # Read file bytes before responding
    file_bytes = await file.read()

    # Validate file size (500MB limit)
    if len(file_bytes) > 500 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 500MB.",
        )
    log_event(
        category="upload",
        event="upload.accepted",
        status="done",
        message="Accepted audio upload",
        job_id=job_id,
        metadata={"size_bytes": len(file_bytes)},
    )

    # Save uploaded file
    original_path = os.path.join(UPLOADS_DIR, f"{job_id}_{file.filename}")
    async with aiofiles.open(original_path, "wb") as f:
        await f.write(file_bytes)

    # Check for missing audio track (common with screen recordings / silent videos)
    if detect_no_audio_track(original_path):
        log_event(
            category="upload",
            event="upload.audio_track",
            status="failed",
            level="error",
            message="Uploaded file has no audio track",
            job_id=job_id,
        )
        os.remove(original_path)
        raise HTTPException(
            status_code=422,
            detail="This video has no audio — nothing to transcribe",
        )

    # Convert to 16kHz mono WAV
    wav_path = os.path.join(UPLOADS_DIR, f"{job_id}.wav")
    try:
        with step_timer("upload.convert", category="upload", job_id=job_id):
            convert_to_wav(original_path, wav_path)
    except subprocess.CalledProcessError:
        # Clean up original file on conversion failure
        if os.path.exists(original_path):
            os.remove(original_path)
        raise HTTPException(
            status_code=422,
            detail="File conversion failed — the file may be corrupt or use an unsupported codec",
        )

    # Clean up original file after successful conversion (save disk space)
    if original_path != wav_path and os.path.exists(original_path):
        os.remove(original_path)

    # Create job and enqueue
    create_job(job_id, wav_path, file.filename)
    await job_queue.put((job_id, "stt"))
    log_event(
        category="pipeline",
        event="job.queued",
        status="done",
        message="Queued recording for transcription",
        job_id=job_id,
        metadata={"stage": "stt"},
    )

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


@app.get("/recordings/{job_id}/transcript/stream")
async def stream_recording_transcript(job_id: str):
    """Server-sent events stream of chunk transcripts as they finish.

    Each event payload is JSON with shape:
        { "kind": "chunk", "seq": N, "start": s, "end": s, "segments": [...] }
        { "kind": "finalized", "duration": s, "n_segments": N }
        { "kind": "heartbeat" }
    Speakers are not assigned until finalize; chunk segments carry no
    speaker field (or "pending").
    """
    import json as _json

    from fastapi.responses import StreamingResponse

    from streaming import progress_store

    async def _gen():
        sent_seqs: set[int] = set()
        idle_ticks = 0
        # Cap total runtime so a stale connection can't hold a worker
        # forever; the frontend reconnects automatically.
        max_seconds = 60 * 60 * 4  # 4h
        elapsed = 0
        while elapsed < max_seconds:
            state = progress_store.get_state(job_id)
            if state is None:
                yield f"data: {_json.dumps({'kind': 'unknown'})}\n\n"
                return
            rows = progress_store.list_chunks_for_recording(
                job_id, pipeline_version=state["pipeline_version"]
            )
            new_done = [r for r in rows if r["state"] == "done" and r["chunk_seq"] not in sent_seqs]
            for r in new_done:
                stt = _json.loads(r.get("stt_segments_json") or "[]")
                offset = float(r.get("seconds_start") or 0.0)
                segments = [
                    {
                        "start": offset + float(s.get("start", 0.0)),
                        "end": offset + float(s.get("end", 0.0)),
                        "text": s.get("text", ""),
                        "speaker": "pending",
                    }
                    for s in stt
                ]
                payload = {
                    "kind": "chunk",
                    "seq": r["chunk_seq"],
                    "start": offset,
                    "end": offset + (float(r.get("seconds_end") or 0.0) - offset),
                    "segments": segments,
                }
                yield f"data: {_json.dumps(payload)}\n\n"
                sent_seqs.add(r["chunk_seq"])
                idle_ticks = 0

            if state["stage"] in ("finalized", "completed"):
                job = get_job(job_id)
                final_payload = {
                    "kind": "finalized",
                    "duration": (job or {}).get("result", {}).get("duration", 0)
                    if job else 0,
                    "n_segments": len((job or {}).get("result", {}).get("segments", []))
                    if job else 0,
                }
                yield f"data: {_json.dumps(final_payload)}\n\n"
                return

            idle_ticks += 1
            if idle_ticks % 5 == 0:
                yield f"data: {_json.dumps({'kind': 'heartbeat'})}\n\n"

            await asyncio.sleep(2)
            elapsed += 2

    return StreamingResponse(_gen(), media_type="text/event-stream")


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


@app.post("/recordings/{job_id}/reprocess", status_code=202)
async def reprocess_recording(job_id: str):
    """Re-run the STT pipeline on an existing recording. Resets transcript,
    extraction, and outcome state, then re-queues the STT job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not os.path.exists(job["file_path"]):
        raise HTTPException(
            status_code=400, detail="Audio file no longer exists on disk"
        )
    update_job(
        job_id,
        status="pending",
        result=None,
        error=None,
        extraction_status="none",
        extraction_error=None,
        outcomes=[],
    )
    await job_queue.put((job_id, "stt"))
    return {"message": "Reprocess enqueued", "job_id": job_id}


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

    from document_generation import build_document_context, generate_prd

    doc_context = build_document_context(job_id)
    with step_timer("document.prd", category="document", job_id=job_id):
        content = await asyncio.to_thread(generate_prd, job_id, app.state, doc_context)
    return {
        "content": content,
        "title": f"PRD - {job.get('original_filename', 'Recording')}",
    }


@app.post("/recordings/{job_id}/generate-diagram")
async def generate_diagram_endpoint(job_id: str):
    """Generate a Mermaid diagram from a recording's transcription.

    Automatically selects the best diagram type (flowchart or erd) based on content.
    Retries with error feedback if the LLM produces invalid Mermaid syntax.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    has_transcript = job.get("result") and job["result"].get("segments")
    has_outcomes = bool(job.get("outcomes"))
    if not has_transcript and not has_outcomes:
        raise HTTPException(status_code=400, detail="No transcription or outcomes to generate from")

    from document_generation import build_document_context, generate_diagram

    doc_context = build_document_context(job_id)
    with step_timer("document.diagram", category="document", job_id=job_id):
        content, diagram_type = await asyncio.to_thread(generate_diagram, job_id, app.state, doc_context)
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
