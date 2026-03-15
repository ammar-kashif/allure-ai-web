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
      { jobId: id, chartStatus: "none", chartPlantuml: null },
      { status: 200 }
    )
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/chart`
    )

    if (!response.ok) {
      return NextResponse.json(
        { jobId: id, chartStatus: "none", chartPlantuml: null },
        { status: 200 }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      jobId: id,
      chartStatus: data.chart_status ?? "none",
      chartPlantuml: data.chart_plantuml ?? null,
    })
  } catch {
    return NextResponse.json(
      { jobId: id, chartStatus: "none", chartPlantuml: null },
      { status: 200 }
    )
  }
}

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
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/chart`,
      { method: "POST" }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }))
      return NextResponse.json(
        { error: error.detail || "Failed to trigger chart generation" },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
