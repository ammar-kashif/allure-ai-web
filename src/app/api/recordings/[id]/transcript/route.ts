import { NextRequest, NextResponse } from "next/server"

import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)

  if (!recording) {
    return NextResponse.json({ error: "Recording not found" }, { status: 404 })
  }

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

    // Transform backend format to frontend Transcript type
    const transcript = {
      id: data.id || recording.backendId,
      recordingId: id,
      duration: data.duration ?? 0,
      speakers: (data.speakers || []).map(
        (spk: { label: string; talk_time_pct: number; utterance_count: number; role?: string }) => ({
          label: spk.label,
          talkTimePct: spk.talk_time_pct,
          utteranceCount: spk.utterance_count,
          ...(spk.role ? { role: spk.role } : {}),
        })
      ),
      utterances: (data.segments || []).map(
        (seg: { start: number; end: number; text: string; speaker: string }, i: number) => ({
          id: `${id}-utt-${i}`,
          speaker: seg.speaker || "Speaker 1",
          text: seg.text,
          startTime: seg.start,
          endTime: seg.end,
        })
      ),
    }

    return NextResponse.json(transcript)
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
