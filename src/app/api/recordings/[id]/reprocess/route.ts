import { NextRequest, NextResponse } from "next/server"

import { getRecording, updateRecording, clearCachedTranscript } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(
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
      `${BACKEND_URL}/recordings/${recording.backendId}/reprocess`,
      { method: "POST" }
    )

    if (!response.ok) {
      const text = await response.text().catch(() => "Unknown error")
      return NextResponse.json(
        { error: text },
        { status: response.status }
      )
    }

    const data = await response.json()
    // Flip local status back to "processing", clear stale description so the
    // post-extraction sync trigger fires, reset titleIsAuto so the new
    // auto-generated title overrides whatever's there (default placeholder
    // OR a previously-manual rename — Reprocess is an explicit "give me a
    // fresh take" signal), and clear the cached transcript so the next
    // /transcript fetch re-pulls from backend.
    updateRecording(id, {
      status: "processing",
      description: null,
      titleIsAuto: true,
    })
    clearCachedTranscript(id)
    return NextResponse.json(data, { status: 202 })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
