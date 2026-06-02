import { getDb } from "./index"
import type { Outcome, EvidenceRef } from "@/types/outcome"

interface OutcomeRow {
  id: string
  recording_id: string
  type: string
  title: string
  detail: string
  confidence: number
  evidence_refs: string
  promoted: number
  promoted_id: string | null
  created_at: string
}

function rowToOutcome(row: OutcomeRow): Outcome {
  let evidenceRefs: EvidenceRef[] = []
  try {
    evidenceRefs = JSON.parse(row.evidence_refs)
  } catch {
    evidenceRefs = []
  }

  return {
    id: row.id,
    type: row.type as Outcome["type"],
    title: row.title,
    detail: row.detail,
    confidence: row.confidence,
    evidenceRefs,
    promoted: row.promoted === 1,
    promotedId: row.promoted_id,
  }
}

export function getOutcomesByRecording(recordingId: string): Outcome[] {
  const db = getDb()
  const rows = db
    .prepare("SELECT * FROM outcomes WHERE recording_id = ? ORDER BY created_at ASC")
    .all(recordingId) as OutcomeRow[]
  return rows.map(rowToOutcome)
}

export function upsertOutcomes(recordingId: string, outcomes: Outcome[]): void {
  const db = getDb()
  const stmt = db.prepare(
    `INSERT OR REPLACE INTO outcomes (id, recording_id, type, title, detail, confidence, evidence_refs, promoted, promoted_id)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )

  const transaction = db.transaction(() => {
    for (const outcome of outcomes) {
      stmt.run(
        outcome.id,
        recordingId,
        outcome.type,
        outcome.title,
        outcome.detail,
        outcome.confidence,
        JSON.stringify(outcome.evidenceRefs),
        outcome.promoted ? 1 : 0,
        outcome.promotedId
      )
    }
  })

  transaction()
}

export function getOutcome(outcomeId: string): Outcome | null {
  const db = getDb()
  const row = db
    .prepare("SELECT * FROM outcomes WHERE id = ?")
    .get(outcomeId) as OutcomeRow | undefined
  return row ? rowToOutcome(row) : null
}

export function updateOutcomePromotion(outcomeId: string, promotedId: string): void {
  const db = getDb()
  db.prepare(
    "UPDATE outcomes SET promoted = 1, promoted_id = ? WHERE id = ?"
  ).run(promotedId, outcomeId)
}

