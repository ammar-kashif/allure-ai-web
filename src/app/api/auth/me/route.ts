import { NextRequest, NextResponse } from "next/server"
import { getSessionUser, isFirstRun } from "@/lib/auth"

export async function GET(request: NextRequest) {
  const firstRun = isFirstRun()
  if (firstRun) {
    return NextResponse.json({ user: null, firstRun: true })
  }

  const user = await getSessionUser(request)
  if (!user) {
    return NextResponse.json({ user: null, firstRun: false }, { status: 401 })
  }
  return NextResponse.json({ user, firstRun: false })
}
