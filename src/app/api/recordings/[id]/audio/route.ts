import { NextRequest, NextResponse } from "next/server"

import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(
  request: NextRequest,
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
    // Forward Range header from the browser so seeking works
    const rangeHeader = request.headers.get("range")
    const headers: HeadersInit = {}
    if (rangeHeader) {
      headers["Range"] = rangeHeader
    }

    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/audio`,
      { headers }
    )

    if (!response.ok && response.status !== 206) {
      return NextResponse.json(
        { error: "Audio not available" },
        { status: response.status }
      )
    }

    const audioBuffer = await response.arrayBuffer()

    return new NextResponse(audioBuffer, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "audio/wav",
        "Content-Length": response.headers.get("content-length") || String(audioBuffer.byteLength),
        "Accept-Ranges": "bytes",
        ...(response.headers.get("content-range")
          ? { "Content-Range": response.headers.get("content-range")! }
          : {}),
        "Cache-Control": "no-cache",
      },
    })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
