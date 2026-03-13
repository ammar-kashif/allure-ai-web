import crypto from "crypto"

import { getDb } from "./index"
import type {
  Task,
  TaskPriority,
  TaskStatus,
  RequirementRecord,
} from "@/types/outcome"

interface TaskRow {
  id: string
  title: string
  detail: string
  source_outcome_id: string | null
  source_recording_id: string | null
  backlink: string | null
  status: string
  priority: string
  due_date: string | null
  assignee: string | null
  tags: string
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
    status: row.status as TaskStatus,
    priority: row.priority as TaskPriority,
    dueDate: row.due_date,
    assignee: row.assignee,
    tags: JSON.parse(row.tags || "[]") as string[],
    createdAt: row.created_at,
    updatedAt: row.updated_at,
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
  id?: string
  title: string
  detail?: string
  sourceOutcomeId?: string
  sourceRecordingId?: string
  backlink?: string
  priority?: TaskPriority
  dueDate?: string | null
  assignee?: string | null
  tags?: string[]
}): Task {
  const db = getDb()
  const id = data.id || crypto.randomUUID()
  const detail = data.detail ?? ""
  const priority = data.priority ?? "medium"
  const tags = JSON.stringify(data.tags ?? [])

  db.prepare(
    `INSERT INTO tasks (id, title, detail, source_outcome_id, source_recording_id, backlink, priority, due_date, assignee, tags)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).run(
    id,
    data.title,
    detail,
    data.sourceOutcomeId ?? null,
    data.sourceRecordingId ?? null,
    data.backlink ?? null,
    priority,
    data.dueDate ?? null,
    data.assignee ?? null,
    tags
  )

  return getTask(id)!
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

export function listTasks(filters?: {
  status?: string | null
  search?: string | null
}): Task[] {
  const db = getDb()
  const conditions: string[] = []
  const params: unknown[] = []

  if (filters?.status) {
    conditions.push("status = ?")
    params.push(filters.status)
  }

  if (filters?.search) {
    conditions.push("(title LIKE ? OR detail LIKE ?)")
    const searchTerm = `%${filters.search}%`
    params.push(searchTerm, searchTerm)
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : ""

  const rows = db
    .prepare(
      `SELECT * FROM tasks ${where}
       ORDER BY
         CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
         created_at DESC`
    )
    .all(...params) as TaskRow[]

  return rows.map(rowToTask)
}

export function updateTask(
  id: string,
  data: Partial<{
    title: string
    detail: string
    status: TaskStatus
    priority: TaskPriority
    dueDate: string | null
    assignee: string | null
    tags: string[]
  }>
): Task | null {
  const db = getDb()

  // Check task exists
  const existing = getTask(id)
  if (!existing) return null

  const sets: string[] = []
  const params: unknown[] = []

  if (data.title !== undefined) {
    sets.push("title = ?")
    params.push(data.title)
  }
  if (data.detail !== undefined) {
    sets.push("detail = ?")
    params.push(data.detail)
  }
  if (data.status !== undefined) {
    sets.push("status = ?")
    params.push(data.status)
  }
  if (data.priority !== undefined) {
    sets.push("priority = ?")
    params.push(data.priority)
  }
  if (data.dueDate !== undefined) {
    sets.push("due_date = ?")
    params.push(data.dueDate)
  }
  if (data.assignee !== undefined) {
    sets.push("assignee = ?")
    params.push(data.assignee)
  }
  if (data.tags !== undefined) {
    sets.push("tags = ?")
    params.push(JSON.stringify(data.tags))
  }

  if (sets.length === 0) return existing

  sets.push("updated_at = datetime('now')")

  db.prepare(`UPDATE tasks SET ${sets.join(", ")} WHERE id = ?`).run(
    ...params,
    id
  )

  return getTask(id)!
}

export function deleteTask(id: string): boolean {
  const db = getDb()
  const result = db.prepare("DELETE FROM tasks WHERE id = ?").run(id)
  return result.changes > 0
}
