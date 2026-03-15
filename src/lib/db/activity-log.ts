import crypto from "crypto"
import { getDb } from "./index"

export interface ActivityEntry {
  id: string
  userId: string | null
  authorName: string
  action: string
  entityType: string
  entityId: string
  detail: string
  createdAt: string
}

interface ActivityRow {
  id: string
  user_id: string | null
  author_name: string
  action: string
  entity_type: string
  entity_id: string
  detail: string
  created_at: string
}

function rowToEntry(row: ActivityRow): ActivityEntry {
  return {
    id: row.id,
    userId: row.user_id,
    authorName: row.author_name,
    action: row.action,
    entityType: row.entity_type,
    entityId: row.entity_id,
    detail: row.detail,
    createdAt: row.created_at,
  }
}

export function logActivity(data: {
  userId?: string | null
  authorName?: string
  action: string
  entityType: string
  entityId: string
  detail?: string
}): void {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO activity_log (id, user_id, author_name, action, entity_type, entity_id, detail)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).run(id, data.userId ?? null, data.authorName ?? "System", data.action, data.entityType, data.entityId, data.detail ?? "")
}

export function listActivity(options?: {
  entityType?: string
  entityId?: string
  limit?: number
}): ActivityEntry[] {
  const db = getDb()
  const conditions: string[] = []
  const params: unknown[] = []

  if (options?.entityType) { conditions.push("entity_type = ?"); params.push(options.entityType) }
  if (options?.entityId) { conditions.push("entity_id = ?"); params.push(options.entityId) }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : ""
  const limit = options?.limit ?? 50
  const rows = db.prepare(
    `SELECT * FROM activity_log ${where} ORDER BY created_at DESC LIMIT ${limit}`
  ).all(...params) as ActivityRow[]
  return rows.map(rowToEntry)
}
