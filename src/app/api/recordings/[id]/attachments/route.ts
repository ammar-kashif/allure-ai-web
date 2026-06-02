import { NextRequest, NextResponse } from "next/server"

import { getRecording } from "@/lib/db/recordings"

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

  if (!recording.backendId) {
    return NextResponse.json(
      { error: "Recording has not been sent to backend" },
      { status: 400 }
    )
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/attachments`
    )

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch attachments" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}

export async function POST(
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
      { status: 400 }
    )
  }

  try {
    const formData = await request.formData()
    const file = formData.get("file") as File | null

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      )
    }

    // Forward as multipart to Python backend
    const backendForm = new FormData()
    backendForm.append("file", file)

    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/attachments`,
      {
        method: "POST",
        body: backendForm,
      }
    )

    if (!response.ok) {
      const text = await response.text().catch(() => "Upload failed")
      return NextResponse.json(
        { error: text },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 201 })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}

