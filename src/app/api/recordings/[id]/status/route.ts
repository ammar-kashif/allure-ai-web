import { NextRequest, NextResponse } from "next/server"

import { getRecording, updateRecording, getCachedTranscript, cacheTranscript } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

/** Pre-fetch and cache transcript when a recording becomes ready. */
async function prefetchTranscript(recordingId: string, backendId: string) {
  // Skip if already cached
  if (getCachedTranscript(recordingId)) return

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

    return NextResponse.json({
      status: mappedStatus,
      extraction_status: data.extraction_status ?? "none",
    })
  } catch {
    // If backend is unavailable, return local status
    return NextResponse.json({ status: recording.status, extraction_status: "none" })
  }
}
