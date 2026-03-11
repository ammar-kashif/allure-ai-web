import { NextRequest, NextResponse } from "next/server"
import { existsSync, mkdirSync, writeFileSync } from "fs"
import { join } from "path"

import { getRecordings, createRecording, updateRecording } from "@/lib/db/recordings"
import type { RecordingStatus } from "@/types/recording"

const RECORDINGS_DIR = join(process.cwd(), "public", "recordings")
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  const status = request.nextUrl.searchParams.get("status") as RecordingStatus | null
  const recordings = getRecordings(status ?? undefined)
  return NextResponse.json(recordings)
}

export async function POST(request: NextRequest) {
  const formData = await request.formData()
  const file = formData.get("file") as File | null
  const recordingId = formData.get("recordingId") as string
  const title = formData.get("title") as string
  const durationMs = Number(formData.get("durationMs") || 0)
  const projectId = formData.get("projectId") as string | null

  if (!file || !recordingId || !title) {
    return NextResponse.json(
      { error: "Missing required fields: file, recordingId, title" },
      { status: 400 }
    )
  }

  // Save file locally
  if (!existsSync(RECORDINGS_DIR)) {
    mkdirSync(RECORDINGS_DIR, { recursive: true })
  }

  const filePath = join(RECORDINGS_DIR, `${recordingId}.webm`)
  const arrayBuffer = await file.arrayBuffer()
  writeFileSync(filePath, Buffer.from(arrayBuffer))

  // Create DB record
  const recording = createRecording({
    id: recordingId,
    title,
    durationMs,
    filePath,
  })

  // If projectId provided, assign and proxy to backend
  if (projectId) {
    try {
      // Update local DB with project assignment
      updateRecording(recordingId, { projectId, status: "processing" })

      // Proxy to FastAPI backend - don't set Content-Type header (let browser set multipart boundary)
      const proxyForm = new FormData()
      proxyForm.append("file", file)

      const backendResponse = await fetch(`${BACKEND_URL}/recordings`, {
        method: "POST",
        body: proxyForm,
      })

      if (backendResponse.ok) {
        const backendData = await backendResponse.json()
        updateRecording(recordingId, { backendId: backendData.id })
      } else {
        updateRecording(recordingId, {
          status: "error",
          errorMessage: "Failed to upload to backend",
        })
      }
    } catch {
      updateRecording(recordingId, {
        status: "error",
        errorMessage: "Backend unavailable",
      })
    }
  }

  return NextResponse.json(recording, { status: 201 })
}
