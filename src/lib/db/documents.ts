import crypto from "crypto"

import { getDb } from "./index"

export interface Document {
  id: string
  title: string
  type: "prd" | "user_flow" | "erd"
  content: string
  sourceRecordingId: string
  createdAt: string
}

interface DocumentRow {
  id: string
  title: string
  type: string
  content: string
  source_recording_id: string
  created_at: string
}

function rowToDocument(row: DocumentRow): Document {
  return {
    id: row.id,
    title: row.title,
    type: row.type as Document["type"],
    content: row.content,
    sourceRecordingId: row.source_recording_id,
    createdAt: row.created_at,
  }
}

export function createDocument(data: {
  title: string
  type: Document["type"]
  content: string
  sourceRecordingId: string
}): Document {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO documents (id, title, type, content, source_recording_id)
     VALUES (?, ?, ?, ?, ?)`
  ).run(id, data.title, data.type, data.content, data.sourceRecordingId)
  return getDocument(id)!
}

export function getDocument(id: string): Document | null {
  const db = getDb()
  const row = db
    .prepare("SELECT * FROM documents WHERE id = ?")
    .get(id) as DocumentRow | undefined
  return row ? rowToDocument(row) : null
}

export function listDocuments(filters?: {
  type?: string | null
}): Document[] {
  const db = getDb()
  const conditions: string[] = []
  const params: unknown[] = []

  if (filters?.type) {
    conditions.push("type = ?")
    params.push(filters.type)
  }

  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : ""
  const rows = db
    .prepare(
      `SELECT * FROM documents ${where} ORDER BY created_at DESC`
    )
    .all(...params) as DocumentRow[]
  return rows.map(rowToDocument)
}

export function countDocuments(): number {
  const db = getDb()
  const row = db
    .prepare("SELECT COUNT(*) as count FROM documents")
    .get() as { count: number }
  return row.count
}
