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
      { status: 404 }
    )
  }

  try {
    const headers: HeadersInit = {}
    const rangeHeader = request.headers.get("range")
    if (rangeHeader) {
      headers["Range"] = rangeHeader
    }

    const backendRes = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/audio`,
      { headers }
    )

    if (!backendRes.ok) {
      return NextResponse.json(
        { error: "Audio not available" },
        { status: backendRes.status }
      )
    }

    const responseHeaders: Record<string, string> = {
      "Content-Type": "audio/wav",
      "Accept-Ranges": "bytes",
    }

    const contentLength = backendRes.headers.get("content-length")
    if (contentLength) {
      responseHeaders["Content-Length"] = contentLength
    }

    const contentRange = backendRes.headers.get("content-range")
    if (contentRange) {
      responseHeaders["Content-Range"] = contentRange
    }

    return new Response(backendRes.body, {
      status: backendRes.status,
      headers: responseHeaders,
    })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
