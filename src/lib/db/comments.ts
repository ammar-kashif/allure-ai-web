import crypto from "crypto"
import { getDb } from "./index"

export type CommentEntityType = "task" | "outcome" | "recording" | "milestone"

export interface Comment {
  id: string
  userId: string | null
  authorName: string
  entityType: CommentEntityType
  entityId: string
  parentId: string | null
  body: string
  replies?: Comment[]
  createdAt: string
  updatedAt: string
}

interface CommentRow {
  id: string
  user_id: string | null
  author_name: string
  entity_type: string
  entity_id: string
  parent_id: string | null
  body: string
  created_at: string
  updated_at: string
}

function rowToComment(row: CommentRow): Comment {
  return {
    id: row.id,
    userId: row.user_id,
    authorName: row.author_name,
    entityType: row.entity_type as CommentEntityType,
    entityId: row.entity_id,
    parentId: row.parent_id,
    body: row.body,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export function createComment(data: {
  userId?: string | null
  authorName: string
  entityType: CommentEntityType
  entityId: string
  parentId?: string | null
  body: string
}): Comment {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO comments (id, user_id, author_name, entity_type, entity_id, parent_id, body)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).run(id, data.userId ?? null, data.authorName, data.entityType, data.entityId, data.parentId ?? null, data.body)
  return getComment(id)!
}

export function getComment(id: string): Comment | null {
  const db = getDb()
  const row = db.prepare("SELECT * FROM comments WHERE id = ?").get(id) as CommentRow | undefined
  return row ? rowToComment(row) : null
}

export function listComments(entityType: CommentEntityType, entityId: string): Comment[] {
  const db = getDb()
  const rows = db.prepare(
    "SELECT * FROM comments WHERE entity_type = ? AND entity_id = ? ORDER BY created_at ASC"
  ).all(entityType, entityId) as CommentRow[]

  const all = rows.map(rowToComment)
  // Build threaded structure
  const byId = new Map(all.map((c) => [c.id, { ...c, replies: [] as Comment[] }]))
  const roots: Comment[] = []

  for (const c of byId.values()) {
    if (c.parentId && byId.has(c.parentId)) {
      byId.get(c.parentId)!.replies!.push(c)
    } else {
      roots.push(c)
    }
  }
  return roots
}

export function deleteComment(id: string): boolean {
  const db = getDb()
  // Remove replies first
  db.prepare("DELETE FROM comments WHERE parent_id = ?").run(id)
  const result = db.prepare("DELETE FROM comments WHERE id = ?").run(id)
  return result.changes > 0
}
