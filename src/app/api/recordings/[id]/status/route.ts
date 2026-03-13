import { NextRequest, NextResponse } from "next/server"

import { getRecording, updateRecording } from "@/lib/db/recordings"

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

  // If no backend ID, return local status
  if (!recording.backendId) {
    return NextResponse.json({ status: recording.status, extraction_status: "none" })
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/status`
    )

    if (!response.ok) {
      return NextResponse.json({ status: recording.status, extraction_status: "none" })
    }

    const data = await response.json()

    // Map backend status to local status enum
    const statusMap: Record<string, string> = {
      pending: "processing",
      processing: "processing",
      completed: "ready",
      failed: "error",
      ready: "ready",
      error: "error",
    }

    const mappedStatus = statusMap[data.status] || recording.status

    // Update local DB if status changed
    if (mappedStatus !== recording.status) {
      updateRecording(id, {
        status: mappedStatus as "processing" | "ready" | "error",
        ...(data.error ? { errorMessage: data.error } : {}),
      })
    }

    return NextResponse.json({
      status: mappedStatus,
      extraction_status: data.extraction_status ?? "none",
    })
  } catch {
    // If backend is unavailable, return local status
    return NextResponse.json({ status: recording.status, extraction_status: "none" })
  }
}
