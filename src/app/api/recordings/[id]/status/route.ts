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
    return NextResponse.json({
      status: recording.status,
      extraction_status: "none",
      chart_status: "none",
    })
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/status`
    )

    if (!response.ok) {
      return NextResponse.json({
        status: recording.status,
        extraction_status: "none",
        chart_status: "none",
      })
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

    // Update local DB if status or duration changed
    const durationMs = typeof data.duration_ms === "number" ? data.duration_ms : undefined
    if (mappedStatus !== recording.status || (durationMs && recording.durationMs === 0)) {
      updateRecording(id, {
        status: mappedStatus as "processing" | "ready" | "error",
        ...(data.error ? { errorMessage: data.error } : {}),
        ...(durationMs ? { durationMs } : {}),
      })

      // Fire notification when transcript becomes ready
      if (mappedStatus === "ready" && recording.status !== "ready") {
        try {
          const { createNotification } = await import("@/lib/db/notifications")
          createNotification({
            type: "transcript_ready",
            title: "Transcript ready",
            body: `"${recording.title}" has been transcribed and is ready for review.`,
            link: `/recordings/${id}`,
          })
        } catch { /* non-fatal */ }
      }
    }

    return NextResponse.json({
      status: mappedStatus,
      extraction_status: data.extraction_status ?? "none",
      chart_status: data.chart_status ?? "none",
    })
  } catch {
    // If backend is unavailable, return local status
    return NextResponse.json({
      status: recording.status,
      extraction_status: "none",
      chart_status: "none",
    })
  }
}
