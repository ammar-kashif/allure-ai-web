import { NextRequest, NextResponse } from "next/server"
import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)
  if (!recording?.backendId) return NextResponse.json({ error: "Not found" }, { status: 404 })

  const res = await fetch(`${BACKEND_URL}/recordings/${recording.backendId}/documents`)
  const data = await res.json()
  return NextResponse.json(data)
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)
  if (!recording?.backendId) return NextResponse.json({ error: "Not found" }, { status: 404 })

  const formData = await request.formData()
  const res = await fetch(`${BACKEND_URL}/recordings/${recording.backendId}/documents`, {
    method: "POST",
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return NextResponse.json({ error: err.detail || "Upload failed" }, { status: res.status })
  }
  const data = await res.json()
  return NextResponse.json(data, { status: 201 })
}
