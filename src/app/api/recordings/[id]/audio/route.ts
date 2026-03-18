import { NextRequest, NextResponse } from "next/server"
import { existsSync, readFileSync, statSync } from "fs"

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

  // 1. Try backend WAV first (higher quality, converted)
  if (recording.backendId) {
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

      if (backendRes.ok) {
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
      }
    } catch {
      // Backend unavailable, fall through to local file
    }
  }

  // 2. Fallback: serve local webm file
  if (recording.filePath && existsSync(recording.filePath)) {
    const stat = statSync(recording.filePath)
    const fileBuffer = readFileSync(recording.filePath)

    return new Response(fileBuffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/webm",
        "Content-Length": String(stat.size),
        "Accept-Ranges": "bytes",
      },
    })
  }

  return NextResponse.json(
    { error: "Audio not available" },
    { status: 404 }
  )
}
