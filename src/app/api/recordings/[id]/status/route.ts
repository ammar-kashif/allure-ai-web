import { NextRequest, NextResponse } from "next/server"

import {
  getRecording,
  updateRecording,
  getCachedTranscript,
  cacheTranscript,
  clearCachedTranscript,
} from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

/** Pre-fetch and cache transcript when a recording becomes ready.
 *  `forceRefresh=true` bypasses the existing cache (used when extraction
 *  completes after the initial cache was populated). */
async function prefetchTranscript(
  recordingId: string,
  backendId: string,
  forceRefresh = false
) {
  if (!forceRefresh && getCachedTranscript(recordingId)) return
  if (forceRefresh) clearCachedTranscript(recordingId)

  try {
    const res = await fetch(`${BACKEND_URL}/recordings/${backendId}/transcript`)
    if (!res.ok) return
    const data = await res.json()

    const transcript = {
      id: (data.id as string) || backendId,
      recordingId,
      duration: data.duration,
      processingTime: data.processing_time ?? 0,
      speakers: ((data.speakers as Record<string, unknown>[]) || []).map(
        (s: Record<string, unknown>) => ({
          label: s.label,
          talkTimePct: s.talk_time_pct ?? 0,
          utteranceCount: s.utterance_count ?? 0,
          talkTime: s.talk_time ?? 0,
          wordCount: s.word_count ?? 0,
          wpm: s.wpm ?? 0,
          turns: s.turns ?? 0,
          avgTurnDuration: s.avg_turn_duration ?? 0,
          pauses: s.pauses ?? 0,
          avgPauseDuration: s.avg_pause_duration ?? 0,
          customLabel: (s.custom_label as string) || "",
          role: (s.role as string) || "",
        })
      ),
      utterances: (
        (data.segments as { start: number; end: number; text: string; speaker: string }[]) || []
      ).map(
        (seg: { start: number; end: number; text: string; speaker: string }, i: number) => ({
          id: `${recordingId}-utt-${i}`,
          speaker: seg.speaker || "Speaker 1",
          text: seg.text,
          startTime: seg.start,
          endTime: seg.end,
        })
      ),
    }

    cacheTranscript(recordingId, JSON.stringify(transcript))

    // Sync duration from backend (fixes duration showing 0 for uploaded files)
    if (transcript.duration && transcript.duration > 0) {
      updateRecording(recordingId, { durationMs: Math.round(transcript.duration * 1000) })
    }

    // Sync auto-generated meeting title + description from backend.
    // Title is only overwritten if the user hasn't manually renamed (titleIsAuto !== false).
    const localRec = getRecording(recordingId)
    const meetingTitle =
      typeof data.meeting_title === "string" ? data.meeting_title.trim() : ""
    const meetingDescription =
      typeof data.meeting_description === "string"
        ? data.meeting_description.trim()
        : ""
    const updates: Parameters<typeof updateRecording>[1] = {}
    if (meetingTitle && localRec?.titleIsAuto !== false) {
      updates.title = meetingTitle
    }
    if (meetingDescription) {
      updates.description = meetingDescription
    }
    if (Object.keys(updates).length > 0) {
      updateRecording(recordingId, updates)
    }
  } catch {
    // Non-critical — transcript will be fetched on demand
  }
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)

  if (!recording) {
    return NextResponse.json({ error: "Recording not found" }, { status: 404 })
  }

  // If no backend ID, return local status
  if (!recording.backendId) {
    return NextResponse.json({ status: recording.status, extraction_status: "none" })
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/status`
    )

    if (!response.ok) {
      return NextResponse.json({ status: recording.status, extraction_status: "none" })
    }

    const data = await response.json()

    // Map backend status to local status enum
    const statusMap: Record<string, string> = {
      pending: "processing",
      processing: "processing",
      completed: "ready",
      failed: "error",
      ready: "ready",
      error: "error",
    }

    const mappedStatus = statusMap[data.status] || recording.status

    // Update local DB if status changed
    if (mappedStatus !== recording.status) {
      updateRecording(id, {
        status: mappedStatus as "processing" | "ready" | "error",
        ...(data.error ? { errorMessage: data.error } : {}),
      })

      // Pre-fetch transcript when transitioning to ready
      if (mappedStatus === "ready") {
        prefetchTranscript(id, recording.backendId).catch(() => {})
      }
    }

    // Race fix: status flips to "ready" before extraction completes, so the
    // first prefetch caches a transcript WITHOUT meeting_title/description.
    // When extraction later completes, force-refresh the cache so title/desc
    // sync into the local recordings row. AWAIT this — the client invalidates
    // ["recording", id] right after this response returns, so the DB write
    // must be committed before we return or the refetch reads stale title.
    if (
      mappedStatus === "ready" &&
      data.extraction_status === "completed" &&
      !recording.description
    ) {
      try {
        await prefetchTranscript(id, recording.backendId, true)
      } catch {
        // best-effort
      }
    }

    return NextResponse.json({
      status: mappedStatus,
      extraction_status: data.extraction_status ?? "none",
    })
  } catch {
    // If backend is unavailable, return local status
    return NextResponse.json({ status: recording.status, extraction_status: "none" })
  }
}
