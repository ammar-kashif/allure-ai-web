import { NextResponse } from "next/server"
import { markAllNotificationsRead } from "@/lib/db/notifications"

export async function POST() {
  markAllNotificationsRead()
  return NextResponse.json({ ok: true })
}
