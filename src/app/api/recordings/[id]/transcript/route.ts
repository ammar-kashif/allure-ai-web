import { NextRequest, NextResponse } from "next/server"

import { getRecording, getCachedTranscript, cacheTranscript } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

function transformBackendData(data: Record<string, unknown>, recordingId: string) {
  return {
    id: (data.id as string) || recordingId,
    recordingId,
    duration: data.duration as number | undefined,
    processingTime: (data.processing_time as number | undefined) ?? 0,
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
      (data.segments as { start: number; end: number; text: string; speaker: string }[]) ||
      []
    ).map(
      (
        seg: { start: number; end: number; text: string; speaker: string },
        i: number
      ) => ({
        id: `${recordingId}-utt-${i}`,
        speaker: seg.speaker || "Speaker 1",
        text: seg.text,
        startTime: seg.start,
        endTime: seg.end,
      })
    ),
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

  // 1. Try local cache first
  const cached = getCachedTranscript(id)
  if (cached) {
    try {
      return NextResponse.json(JSON.parse(cached))
    } catch {
      // Corrupted cache, fall through to backend
    }
  }

  // 2. Fetch from backend
  if (!recording.backendId) {
    return NextResponse.json(
      { error: "Recording has not been sent to backend" },
      { status: 400 }
    )
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/transcript`
    )

    if (!response.ok) {
      return NextResponse.json(
        { error: "Transcript not available" },
        { status: response.status }
      )
    }

    const data = await response.json()
    const transcript = transformBackendData(data, id)

    // 3. Cache locally for instant access next time
    cacheTranscript(id, JSON.stringify(transcript))

    return NextResponse.json(transcript)
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}

