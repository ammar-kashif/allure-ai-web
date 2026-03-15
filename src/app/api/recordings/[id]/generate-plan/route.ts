import { NextRequest, NextResponse } from "next/server"
import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const recording = getRecording(id)
  if (!recording?.backendId) return NextResponse.json({ error: "Not found" }, { status: 404 })

  const body = await request.json().catch(() => ({}))

  const res = await fetch(`${BACKEND_URL}/recordings/${recording.backendId}/generate-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return NextResponse.json({ error: err.detail || "Plan generation failed" }, { status: res.status })
  }

  const plan = await res.json()
  return NextResponse.json(plan)
}
