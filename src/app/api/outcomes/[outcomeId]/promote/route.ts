import { NextRequest, NextResponse } from "next/server"

import { getRecording } from "@/lib/db/recordings"
import { updateOutcomePromotion } from "@/lib/db/outcomes"
import { createTask, createRequirementRecord } from "@/lib/db/tasks"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

interface PromoteRequestBody {
  recordingId: string
  outcomeIndex: number
}

interface PromoteResponse {
  id: string
  type: string
  backlink: string
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ outcomeId: string }> }
) {
  const { outcomeId } = await params
  const body: PromoteRequestBody = await request.json()
  const { recordingId, outcomeIndex } = body

  if (!recordingId || outcomeIndex === undefined) {
    return NextResponse.json(
      { error: "recordingId and outcomeIndex are required" },
      { status: 400 }
    )
  }

  // Look up the backend job ID from the frontend recording
  const recording = getRecording(recordingId)
  if (!recording) {
    return NextResponse.json(
      { error: "Recording not found" },
      { status: 404 }
    )
  }
  if (!recording.backendId) {
    return NextResponse.json(
      { error: "Recording has not been sent to backend" },
      { status: 400 }
    )
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/outcomes/${outcomeIndex}/promote`,
      { method: "POST" }
    )

    if (!response.ok) {
      const text = await response.text().catch(() => "Unknown error")
      return NextResponse.json(
        { error: text },
        { status: response.status }
      )
    }

    const data: PromoteResponse = await response.json()

    // Update frontend SQLite: mark outcome as promoted
    updateOutcomePromotion(outcomeId, data.id)

    // Create the promoted record in frontend SQLite based on type
    // Backend returns "task" for action_items and "requirement" for requirements
    const commonData = {
      id: data.id,
      title: "",
      detail: "",
      sourceOutcomeId: outcomeId,
      sourceRecordingId: recordingId,
      backlink: data.backlink,
    }

    if (data.type === "task") {
      createTask(commonData)
    } else if (data.type === "requirement") {
      createRequirementRecord(commonData)
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
