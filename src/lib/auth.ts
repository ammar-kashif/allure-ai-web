import crypto from "crypto"
import { cookies } from "next/headers"
import { NextRequest } from "next/server"
import { getDb } from "@/lib/db/index"

export interface SessionUser {
  id: string
  email: string
  name: string
  role: "admin" | "viewer"
}

const SESSION_COOKIE = "allure_session"
const SESSION_DURATION_DAYS = 7

// ---------------------------------------------------------------------------
// Password hashing (scrypt, no external deps)
// ---------------------------------------------------------------------------

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex")
  const hash = crypto.scryptSync(password, salt, 64).toString("hex")
  return `${salt}:${hash}`
}

export function verifyPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(":")
  if (!salt || !hash) return false
  const derived = crypto.scryptSync(password, salt, 64).toString("hex")
  return crypto.timingSafeEqual(Buffer.from(derived, "hex"), Buffer.from(hash, "hex"))
}

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------

export function createSession(userId: string): string {
  const db = getDb()
  const sessionId = crypto.randomUUID()
  const expiresAt = new Date(Date.now() + SESSION_DURATION_DAYS * 86400 * 1000).toISOString()
  db.prepare(
    "INSERT INTO user_sessions (id, user_id, expires_at) VALUES (?, ?, ?)"
  ).run(sessionId, userId, expiresAt)
  return sessionId
}

export function deleteSession(sessionId: string): void {
  const db = getDb()
  db.prepare("DELETE FROM user_sessions WHERE id = ?").run(sessionId)
}

export function getUserFromSession(sessionId: string): SessionUser | null {
  const db = getDb()
  const row = db.prepare(`
    SELECT u.id, u.email, u.name, u.role
    FROM user_sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.id = ? AND s.expires_at > datetime('now')
  `).get(sessionId) as SessionUser | undefined
  return row ?? null
}

// ---------------------------------------------------------------------------
// Helpers for API routes
// ---------------------------------------------------------------------------

export async function getSessionUser(request: NextRequest): Promise<SessionUser | null> {
  const cookie = request.cookies.get(SESSION_COOKIE)
  if (!cookie) return null
  return getUserFromSession(cookie.value)
}

export async function getSessionUserFromCookies(): Promise<SessionUser | null> {
  const cookieStore = await cookies()
  const cookie = cookieStore.get(SESSION_COOKIE)
  if (!cookie) return null
  return getUserFromSession(cookie.value)
}

export function setSessionCookie(response: Response, sessionId: string) {
  const expires = new Date(Date.now() + SESSION_DURATION_DAYS * 86400 * 1000)
  response.headers.append(
    "Set-Cookie",
    `${SESSION_COOKIE}=${sessionId}; Path=/; HttpOnly; SameSite=Lax; Expires=${expires.toUTCString()}`
  )
}

export function clearSessionCookie(response: Response) {
  response.headers.append(
    "Set-Cookie",
    `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Expires=Thu, 01 Jan 1970 00:00:00 GMT`
  )
}

// ---------------------------------------------------------------------------
// First-run check
// ---------------------------------------------------------------------------

export function hasAnyUser(): boolean {
  const db = getDb()
  const row = db.prepare("SELECT COUNT(*) as count FROM users").get() as { count: number }
  return row.count > 0
}

export function isFirstRun(): boolean {
  return !hasAnyUser()
}
