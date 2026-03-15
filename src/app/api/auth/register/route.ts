import { NextRequest, NextResponse } from "next/server"
import { createUser, getUserByEmail } from "@/lib/db/users"
import { createSession, setSessionCookie, isFirstRun } from "@/lib/auth"

export async function POST(request: NextRequest) {
  try {
    const { email, name, password, role } = await request.json()

    if (!email || !name || !password) {
      return NextResponse.json({ error: "email, name, and password are required" }, { status: 400 })
    }

    if (password.length < 6) {
      return NextResponse.json({ error: "Password must be at least 6 characters" }, { status: 400 })
    }

    // Only the very first registration can create an admin; subsequent registrations via this endpoint
    // are always viewers (admin invites handled separately).
    const firstRun = isFirstRun()
    const assignedRole = firstRun ? "admin" : (role === "admin" ? "viewer" : (role ?? "viewer"))

    const existing = getUserByEmail(email)
    if (existing) {
      return NextResponse.json({ error: "Email already registered" }, { status: 409 })
    }

    const user = createUser({ email, name, password, role: assignedRole })
    const sessionId = createSession(user.id)

    const response = NextResponse.json({ user }, { status: 201 })
    setSessionCookie(response, sessionId)
    return response
  } catch {
    return NextResponse.json({ error: "Registration failed" }, { status: 500 })
  }
}
