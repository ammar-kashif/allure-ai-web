import crypto from "crypto"
import { getDb } from "./index"

export interface Notification {
  id: string
  userId: string | null
  type: string
  title: string
  body: string
  link: string | null
  read: boolean
  createdAt: string
}

interface NotificationRow {
  id: string
  user_id: string | null
  type: string
  title: string
  body: string
  link: string | null
  read: number
  created_at: string
}

function rowToNotification(row: NotificationRow): Notification {
  return {
    id: row.id,
    userId: row.user_id,
    type: row.type,
    title: row.title,
    body: row.body,
    link: row.link,
    read: row.read === 1,
    createdAt: row.created_at,
  }
}

export function createNotification(data: {
  userId?: string | null
  type: string
  title: string
  body?: string
  link?: string | null
}): Notification {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    "INSERT INTO notifications (id, user_id, type, title, body, link) VALUES (?, ?, ?, ?, ?, ?)"
  ).run(id, data.userId ?? null, data.type, data.title, data.body ?? "", data.link ?? null)
  return getNotification(id)!
}

export function getNotification(id: string): Notification | null {
  const db = getDb()
  const row = db.prepare("SELECT * FROM notifications WHERE id = ?").get(id) as NotificationRow | undefined
  return row ? rowToNotification(row) : null
}

export function listNotifications(options?: {
  userId?: string | null
  unreadOnly?: boolean
  limit?: number
}): Notification[] {
  const db = getDb()
  const conditions: string[] = []
  const params: unknown[] = []

  if (options?.userId !== undefined) {
    conditions.push("(user_id = ? OR user_id IS NULL)")
    params.push(options.userId)
  }
  if (options?.unreadOnly) {
    conditions.push("read = 0")
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : ""
  const limit = options?.limit ? `LIMIT ${options.limit}` : "LIMIT 50"
  const rows = db.prepare(
    `SELECT * FROM notifications ${where} ORDER BY created_at DESC ${limit}`
  ).all(...params) as NotificationRow[]
  return rows.map(rowToNotification)
}

export function markNotificationRead(id: string): void {
  const db = getDb()
  db.prepare("UPDATE notifications SET read = 1 WHERE id = ?").run(id)
}

export function markAllNotificationsRead(userId?: string | null): void {
  const db = getDb()
  if (userId) {
    db.prepare("UPDATE notifications SET read = 1 WHERE user_id = ? OR user_id IS NULL").run(userId)
  } else {
    db.prepare("UPDATE notifications SET read = 1").run()
  }
}

export function countUnreadNotifications(userId?: string | null): number {
  const db = getDb()
  const row = userId
    ? db.prepare("SELECT COUNT(*) as count FROM notifications WHERE (user_id = ? OR user_id IS NULL) AND read = 0").get(userId) as { count: number }
    : db.prepare("SELECT COUNT(*) as count FROM notifications WHERE read = 0").get() as { count: number }
  return row?.count ?? 0
}
