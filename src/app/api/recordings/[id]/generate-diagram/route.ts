import { NextRequest, NextResponse } from "next/server"

import { createDocument } from "@/lib/db/documents"
import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(
  _request: NextRequest,
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
    const backendRes = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/generate-diagram`,
      { method: "POST" }
    )

    if (!backendRes.ok) {
      const errorText = await backendRes.text().catch(() => "Backend error")
      return NextResponse.json(
        { error: errorText },
        { status: backendRes.status }
      )
    }

    const data = await backendRes.json()

    const doc = createDocument({
      title: data.title,
      type: data.type,
      content: data.content,
      sourceRecordingId: id,
    })

    return NextResponse.json(doc, { status: 201 })
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 502 }
    )
  }
}
