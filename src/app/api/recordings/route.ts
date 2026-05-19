import { NextRequest, NextResponse } from "next/server"
import { existsSync, mkdirSync, writeFileSync } from "fs"
import { join } from "path"

import { getRecordings, getRecording, createRecording, updateRecording } from "@/lib/db/recordings"
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

  // Validate file size (500MB limit)
  const MAX_FILE_SIZE = 500 * 1024 * 1024
  if (file.size > MAX_FILE_SIZE) {
    return NextResponse.json(
      { error: "File too large. Maximum size is 500MB." },
      { status: 413 }
    )
  }

  // Idempotency: a retried upload (e.g. the meeting-bot forwarder retrying
  // on a transient error) must not 500 on the UNIQUE PK. If a row with this
  // id already exists, treat the request as a no-op and return the existing
  // row -- the original upload's pipeline is already running.
  const existing = getRecording(recordingId)
  if (existing) {
    return NextResponse.json(existing, { status: 200 })
  }

  // Save file locally
  if (!existsSync(RECORDINGS_DIR)) {
    mkdirSync(RECORDINGS_DIR, { recursive: true })
  }

  const ext = file.name.split('.').pop() || 'webm'
  const filePath = join(RECORDINGS_DIR, `${recordingId}.${ext}`)
  const arrayBuffer = await file.arrayBuffer()
  writeFileSync(filePath, Buffer.from(arrayBuffer))

  // Create DB record
  const recording = createRecording({
    id: recordingId,
    title,
    durationMs,
    filePath,
  })

  // Assign project if provided
  if (projectId) {
    updateRecording(recordingId, { projectId })
  }

  // Always proxy to backend for transcription
  try {
    updateRecording(recordingId, { status: "processing" })

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

  return NextResponse.json(recording, { status: 201 })
}
