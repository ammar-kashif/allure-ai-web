import crypto from "crypto"
import { getDb } from "./index"

export interface Milestone {
  id: string
  projectId: string
  title: string
  detail: string
  startDate: string | null
  endDate: string | null
  status: "upcoming" | "in_progress" | "completed"
  createdBy: string | null
  createdAt: string
  updatedAt: string
  progress?: MilestoneProgress
}

export interface MilestoneProgress {
  total: number
  todo: number
  inProgress: number
  done: number
  pct: number
}

interface MilestoneRow {
  id: string
  project_id: string
  title: string
  detail: string
  start_date: string | null
  end_date: string | null
  status: string
  created_by: string | null
  created_at: string
  updated_at: string
}

function rowToMilestone(row: MilestoneRow): Milestone {
  return {
    id: row.id,
    projectId: row.project_id,
    title: row.title,
    detail: row.detail,
    startDate: row.start_date,
    endDate: row.end_date,
    status: row.status as Milestone["status"],
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export function createMilestone(data: {
  projectId: string
  title: string
  detail?: string
  startDate?: string | null
  endDate?: string | null
  createdBy?: string | null
}): Milestone {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO milestones (id, project_id, title, detail, start_date, end_date, created_by)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).run(id, data.projectId, data.title, data.detail ?? "", data.startDate ?? null, data.endDate ?? null, data.createdBy ?? null)
  return getMilestone(id)!
}

export function getMilestone(id: string): Milestone | null {
  const db = getDb()
  const row = db.prepare("SELECT * FROM milestones WHERE id = ?").get(id) as MilestoneRow | undefined
  if (!row) return null
  const milestone = rowToMilestone(row)
  milestone.progress = getMilestoneProgress(id)
  return milestone
}

export function listMilestones(projectId?: string): Milestone[] {
  const db = getDb()
  const rows = projectId
    ? (db.prepare("SELECT * FROM milestones WHERE project_id = ? ORDER BY start_date ASC, created_at ASC").all(projectId) as MilestoneRow[])
    : (db.prepare("SELECT * FROM milestones ORDER BY start_date ASC, created_at ASC").all() as MilestoneRow[])
  return rows.map((row) => {
    const m = rowToMilestone(row)
    m.progress = getMilestoneProgress(m.id)
    return m
  })
}

export function updateMilestone(
  id: string,
  data: Partial<{
    title: string
    detail: string
    startDate: string | null
    endDate: string | null
    status: Milestone["status"]
  }>
): Milestone | null {
  const db = getDb()
  const sets: string[] = []
  const values: unknown[] = []
  if (data.title !== undefined) { sets.push("title = ?"); values.push(data.title) }
  if (data.detail !== undefined) { sets.push("detail = ?"); values.push(data.detail) }
  if (data.startDate !== undefined) { sets.push("start_date = ?"); values.push(data.startDate) }
  if (data.endDate !== undefined) { sets.push("end_date = ?"); values.push(data.endDate) }
  if (data.status !== undefined) { sets.push("status = ?"); values.push(data.status) }
  if (sets.length === 0) return getMilestone(id)
  sets.push("updated_at = datetime('now')")
  values.push(id)
  db.prepare(`UPDATE milestones SET ${sets.join(", ")} WHERE id = ?`).run(...values)
  return getMilestone(id)
}

export function deleteMilestone(id: string): boolean {
  const db = getDb()
  // Unlink tasks first
  db.prepare("UPDATE tasks SET milestone_id = NULL WHERE milestone_id = ?").run(id)
  const result = db.prepare("DELETE FROM milestones WHERE id = ?").run(id)
  return result.changes > 0
}

export function getMilestoneProgress(milestoneId: string): MilestoneProgress {
  const db = getDb()
  const rows = db.prepare(
    "SELECT status, COUNT(*) as count FROM tasks WHERE milestone_id = ? GROUP BY status"
  ).all(milestoneId) as { status: string; count: number }[]
  const counts: Record<string, number> = {}
  let total = 0
  for (const row of rows) {
    counts[row.status] = row.count
    total += row.count
  }
  const done = counts["done"] ?? 0
  const inProgress = counts["in_progress"] ?? 0
  const todo = counts["todo"] ?? 0
  return {
    total,
    todo,
    inProgress,
    done,
    pct: total > 0 ? Math.round((done / total) * 100) : 0,
  }
}

// Task dependencies

export function addTaskDependency(blockerId: string, blockedId: string): void {
  const db = getDb()
  db.prepare(
    "INSERT OR IGNORE INTO task_dependencies (blocker_id, blocked_id) VALUES (?, ?)"
  ).run(blockerId, blockedId)
}

export function removeTaskDependency(blockerId: string, blockedId: string): void {
  const db = getDb()
  db.prepare(
    "DELETE FROM task_dependencies WHERE blocker_id = ? AND blocked_id = ?"
  ).run(blockerId, blockedId)
}

export function getTaskDependencies(taskId: string): { blockedBy: string[]; blocks: string[] } {
  const db = getDb()
  const blockedBy = (db.prepare(
    "SELECT blocker_id FROM task_dependencies WHERE blocked_id = ?"
  ).all(taskId) as { blocker_id: string }[]).map((r) => r.blocker_id)

  const blocks = (db.prepare(
    "SELECT blocked_id FROM task_dependencies WHERE blocker_id = ?"
  ).all(taskId) as { blocked_id: string }[]).map((r) => r.blocked_id)

  return { blockedBy, blocks }
}
