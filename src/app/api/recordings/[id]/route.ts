import { NextRequest, NextResponse } from "next/server"

import { getRecording, updateRecording } from "@/lib/db/recordings"

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
