import { NextRequest, NextResponse } from "next/server"
import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; docIndex: string }> }
) {
  const { id, docIndex } = await params
  const recording = getRecording(id)
  if (!recording?.backendId) return NextResponse.json({ error: "Not found" }, { status: 404 })

  const res = await fetch(`${BACKEND_URL}/recordings/${recording.backendId}/documents/${docIndex}`)
  if (!res.ok) return NextResponse.json({ error: "Not found" }, { status: res.status })
  const data = await res.json()
  return NextResponse.json(data)
}
