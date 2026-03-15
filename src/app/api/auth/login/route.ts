import { NextRequest, NextResponse } from "next/server"
import { getUserByEmail } from "@/lib/db/users"
import { verifyPassword, createSession, setSessionCookie } from "@/lib/auth"

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    if (!email || !password) {
      return NextResponse.json({ error: "email and password are required" }, { status: 400 })
    }

    const userRow = getUserByEmail(email)
    if (!userRow || !verifyPassword(password, userRow.password_hash)) {
      return NextResponse.json({ error: "Invalid email or password" }, { status: 401 })
    }

    const sessionId = createSession(userRow.id)

    const user = {
      id: userRow.id,
      email: userRow.email,
      name: userRow.name,
      role: userRow.role,
    }

    const response = NextResponse.json({ user })
    setSessionCookie(response, sessionId)
    return response
  } catch {
    return NextResponse.json({ error: "Login failed" }, { status: 500 })
  }
}
