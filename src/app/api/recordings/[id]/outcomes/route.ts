import { NextRequest, NextResponse } from "next/server"

import { getRecording } from "@/lib/db/recordings"
import { upsertOutcomes } from "@/lib/db/outcomes"
import type { Outcome, EvidenceRef } from "@/types/outcome"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

interface BackendOutcome {
  id: string
  type: string
  title: string
  detail: string
  confidence: number
  evidence_refs: { segment_index: number; speaker: string; timestamp: number; text_snippet?: string }[]
  promoted: boolean
  promoted_id: string | null
}

interface BackendOutcomesResponse {
  job_id: string
  extraction_status: string
  outcomes: BackendOutcome[]
}

function transformOutcome(bo: BackendOutcome): Outcome {
  return {
    id: bo.id,
    type: bo.type as Outcome["type"],
    title: bo.title,
    detail: bo.detail,
    confidence: bo.confidence,
    evidenceRefs: (bo.evidence_refs || []).map(
      (ref): EvidenceRef => ({
        segmentIndex: ref.segment_index,
        speaker: ref.speaker,
        timestamp: ref.timestamp,
        textSnippet: ref.text_snippet,
      })
    ),
    promoted: bo.promoted ?? false,
    promotedId: bo.promoted_id ?? null,
  }
}

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
      `${BACKEND_URL}/recordings/${recording.backendId}/outcomes`
    )

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({
          jobId: "",
          extractionStatus: "none",
          outcomes: [],
        })
      }
      return NextResponse.json(
        { error: "Failed to fetch outcomes" },
        { status: response.status }
      )
    }

    const data: BackendOutcomesResponse = await response.json()
    const outcomes = (data.outcomes || []).map(transformOutcome)

    // Persist outcomes to frontend SQLite for offline resilience
    if (outcomes.length > 0) {
      upsertOutcomes(id, outcomes)
    }

    return NextResponse.json({
      jobId: data.job_id,
      extractionStatus: data.extraction_status,
      outcomes,
    })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}

