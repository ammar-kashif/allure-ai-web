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
    return NextResponse.json({ run: null, actions: [] })
  }
  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/autonomy`
    )
    const text = await response.text()
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 })
  }
}
