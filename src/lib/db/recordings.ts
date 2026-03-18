import { getDb } from "./index"
import type { Recording, RecordingStatus } from "@/types/recording"

interface RecordingRow {
  id: string
  title: string
  duration_ms: number
  file_path: string | null
  status: string
  project_id: string | null
  backend_id: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

function rowToRecording(row: RecordingRow): Recording {
  return {
    id: row.id,
    title: row.title,
    durationMs: row.duration_ms,
    filePath: row.file_path,
    status: row.status as RecordingStatus,
    projectId: row.project_id,
    backendId: row.backend_id,
    errorMessage: row.error_message,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export function getRecordings(status?: RecordingStatus): Recording[] {
  const db = getDb()
  if (status) {
    const rows = db
      .prepare("SELECT * FROM recordings WHERE status = ? ORDER BY created_at DESC")
      .all(status) as RecordingRow[]
    return rows.map(rowToRecording)
  }
  const rows = db
    .prepare("SELECT * FROM recordings ORDER BY created_at DESC")
    .all() as RecordingRow[]
  return rows.map(rowToRecording)
}

export function getRecording(id: string): Recording | null {
  const db = getDb()
  const row = db
    .prepare("SELECT * FROM recordings WHERE id = ?")
    .get(id) as RecordingRow | undefined
  return row ? rowToRecording(row) : null
}

export function createRecording(data: {
  id: string
  title: string
  durationMs: number
  filePath: string
}): Recording {
  const db = getDb()
  db.prepare(
    `INSERT INTO recordings (id, title, duration_ms, file_path, status)
     VALUES (?, ?, ?, ?, 'unassigned')`
  ).run(data.id, data.title, data.durationMs, data.filePath)

  return getRecording(data.id)!
}

export function updateRecording(
  id: string,
  data: Partial<Pick<Recording, "title" | "status" | "projectId" | "backendId" | "errorMessage">>
): Recording {
  const db = getDb()
  const sets: string[] = []
  const values: unknown[] = []

  if (data.title !== undefined) {
    sets.push("title = ?")
    values.push(data.title)
  }
  if (data.status !== undefined) {
    sets.push("status = ?")
    values.push(data.status)
  }
  if (data.projectId !== undefined) {
    sets.push("project_id = ?")
    values.push(data.projectId)
  }
  if (data.backendId !== undefined) {
    sets.push("backend_id = ?")
    values.push(data.backendId)
  }
  if (data.errorMessage !== undefined) {
    sets.push("error_message = ?")
    values.push(data.errorMessage)
  }

  sets.push("updated_at = datetime('now')")
  values.push(id)

  db.prepare(`UPDATE recordings SET ${sets.join(", ")} WHERE id = ?`).run(
    ...values
  )

  return getRecording(id)!
}

export function deleteRecording(id: string): void {
  const db = getDb()
  // Delete related rows first (foreign key order)
  db.prepare("DELETE FROM tasks WHERE source_recording_id = ?").run(id)
  db.prepare("DELETE FROM requirement_records WHERE source_recording_id = ?").run(id)
  db.prepare("DELETE FROM outcomes WHERE recording_id = ?").run(id)
  db.prepare("DELETE FROM recordings WHERE id = ?").run(id)
}

export function getCachedTranscript(id: string): string | null {
  const db = getDb()
  const row = db
    .prepare("SELECT transcript_data FROM recordings WHERE id = ?")
    .get(id) as { transcript_data: string | null } | undefined
  return row?.transcript_data ?? null
}

export function cacheTranscript(id: string, data: string): void {
  const db = getDb()
  db.prepare("UPDATE recordings SET transcript_data = ? WHERE id = ?").run(data, id)
}

export function clearCachedTranscript(id: string): void {
  const db = getDb()
  db.prepare("UPDATE recordings SET transcript_data = NULL WHERE id = ?").run(id)
}

export function getRecordingCounts(): Record<RecordingStatus | "all", number> {
  const db = getDb()
  const rows = db
    .prepare(
      "SELECT status, COUNT(*) as count FROM recordings GROUP BY status"
    )
    .all() as { status: string; count: number }[]

  const counts: Record<string, number> = {
    all: 0,
    unassigned: 0,
    processing: 0,
    ready: 0,
    error: 0,
  }

  for (const row of rows) {
    counts[row.status] = row.count
    counts.all += row.count
  }

  return counts as Record<RecordingStatus | "all", number>
}
