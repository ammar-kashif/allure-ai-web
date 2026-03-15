import crypto from "crypto"
import { getDb } from "./index"
import { hashPassword } from "@/lib/auth"

export interface UserRow {
  id: string
  email: string
  name: string
  password_hash: string
  role: "admin" | "viewer"
  created_at: string
}

export interface PublicUser {
  id: string
  email: string
  name: string
  role: "admin" | "viewer"
  createdAt: string
}

function rowToPublicUser(row: UserRow): PublicUser {
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    role: row.role,
    createdAt: row.created_at,
  }
}

export function createUser(data: {
  email: string
  name: string
  password: string
  role?: "admin" | "viewer"
}): PublicUser {
  const db = getDb()
  const id = crypto.randomUUID()
  const password_hash = hashPassword(data.password)
  db.prepare(
    "INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)"
  ).run(id, data.email.toLowerCase().trim(), data.name.trim(), password_hash, data.role ?? "viewer")
  return getUserById(id)!
}

export function getUserByEmail(email: string): UserRow | null {
  const db = getDb()
  return (db.prepare("SELECT * FROM users WHERE email = ?").get(email.toLowerCase().trim()) as UserRow | undefined) ?? null
}

export function getUserById(id: string): PublicUser | null {
  const db = getDb()
  const row = db.prepare("SELECT * FROM users WHERE id = ?").get(id) as UserRow | undefined
  return row ? rowToPublicUser(row) : null
}

export function listUsers(): PublicUser[] {
  const db = getDb()
  return (db.prepare("SELECT * FROM users ORDER BY created_at ASC").all() as UserRow[]).map(rowToPublicUser)
}

export function updateUser(
  id: string,
  data: Partial<{ name: string; role: "admin" | "viewer" }>
): PublicUser | null {
  const db = getDb()
  const sets: string[] = []
  const values: unknown[] = []
  if (data.name !== undefined) { sets.push("name = ?"); values.push(data.name.trim()) }
  if (data.role !== undefined) { sets.push("role = ?"); values.push(data.role) }
  if (sets.length === 0) return getUserById(id)
  values.push(id)
  db.prepare(`UPDATE users SET ${sets.join(", ")} WHERE id = ?`).run(...values)
  return getUserById(id)
}

export function deleteUser(id: string): void {
  const db = getDb()
  db.prepare("DELETE FROM users WHERE id = ?").run(id)
}
