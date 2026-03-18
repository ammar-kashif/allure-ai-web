import { NextRequest, NextResponse } from "next/server"

import { getRecording, clearCachedTranscript } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; label: string }> }
) {
  const { id, label } = await params
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
    const body = await request.json()

    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/speakers/${encodeURIComponent(label)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    )

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error")
      return NextResponse.json(
        { error: errorText },
        { status: response.status }
      )
    }

    // Clear cached transcript so next fetch picks up updated speaker data
    clearCachedTranscript(id)

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
