import { getDb } from "./index"
import type { Task, RequirementRecord } from "@/types/outcome"

interface TaskRow {
  id: string
  title: string
  detail: string
  source_outcome_id: string
  source_recording_id: string
  backlink: string
  status: string
  created_at: string
  updated_at: string
}

interface RequirementRow {
  id: string
  title: string
  detail: string
  source_outcome_id: string
  source_recording_id: string
  backlink: string
  created_at: string
  updated_at: string
}

function rowToTask(row: TaskRow): Task {
  return {
    id: row.id,
    title: row.title,
    detail: row.detail,
    sourceOutcomeId: row.source_outcome_id,
    sourceRecordingId: row.source_recording_id,
    backlink: row.backlink,
    status: row.status,
    createdAt: row.created_at,
  }
}

function rowToRequirementRecord(row: RequirementRow): RequirementRecord {
  return {
    id: row.id,
    title: row.title,
    detail: row.detail,
    sourceOutcomeId: row.source_outcome_id,
    sourceRecordingId: row.source_recording_id,
    backlink: row.backlink,
    createdAt: row.created_at,
  }
}

export function createTask(data: {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string
  sourceRecordingId: string
  backlink: string
}): Task {
  const db = getDb()
  db.prepare(
    `INSERT INTO tasks (id, title, detail, source_outcome_id, source_recording_id, backlink)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(data.id, data.title, data.detail, data.sourceOutcomeId, data.sourceRecordingId, data.backlink)

  return getTask(data.id)!
}

export function createRequirementRecord(data: {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string
  sourceRecordingId: string
  backlink: string
}): RequirementRecord {
  const db = getDb()
  db.prepare(
    `INSERT INTO requirement_records (id, title, detail, source_outcome_id, source_recording_id, backlink)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(data.id, data.title, data.detail, data.sourceOutcomeId, data.sourceRecordingId, data.backlink)

  return getRequirementRecord(data.id)!
}

export function getTask(id: string): Task | null {
  const db = getDb()
  const row = db
    .prepare("SELECT * FROM tasks WHERE id = ?")
    .get(id) as TaskRow | undefined
  return row ? rowToTask(row) : null
}

export function getRequirementRecord(id: string): RequirementRecord | null {
  const db = getDb()
  const row = db
    .prepare("SELECT * FROM requirement_records WHERE id = ?")
    .get(id) as RequirementRow | undefined
  return row ? rowToRequirementRecord(row) : null
}
