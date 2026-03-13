import { existsSync, unlinkSync } from "fs"
import { join } from "path"

import { NextRequest, NextResponse } from "next/server"

import { deleteRecording, getRecording, updateRecording } from "@/lib/db/recordings"

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
  return NextResponse.json(recording)
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const body = await request.json()
  const recording = getRecording(id)

  if (!recording) {
    return NextResponse.json({ error: "Recording not found" }, { status: 404 })
  }

  const updated = updateRecording(id, body)
  return NextResponse.json(updated)
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)

  if (!recording) {
    return NextResponse.json({ error: "Recording not found" }, { status: 404 })
  }

  // Delete from backend if it has a backend ID (cleans up WAV files)
  if (recording.backendId) {
    try {
      await fetch(`${BACKEND_URL}/recordings/${recording.backendId}`, {
        method: "DELETE",
      })
    } catch {
      // Backend may be unavailable, continue with local cleanup
    }
  }

  // Delete local audio file
  const localAudioPath = join(process.cwd(), "public", "recordings", `${id}.webm`)
  if (existsSync(localAudioPath)) {
    unlinkSync(localAudioPath)
  }

  // Delete from local DB
  deleteRecording(id)

  return new NextResponse(null, { status: 204 })
}
