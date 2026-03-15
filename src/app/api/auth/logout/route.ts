import { NextRequest, NextResponse } from "next/server"
import { deleteSession, clearSessionCookie } from "@/lib/auth"

export async function POST(request: NextRequest) {
  const cookie = request.cookies.get("allure_session")
  if (cookie) {
    deleteSession(cookie.value)
  }
  const response = NextResponse.json({ ok: true })
  clearSessionCookie(response)
  return response
}
