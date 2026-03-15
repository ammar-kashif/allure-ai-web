import { NextRequest, NextResponse } from "next/server"
import { listNotifications, countUnreadNotifications } from "@/lib/db/notifications"

export async function GET(_request: NextRequest) {
  const notifications = listNotifications({ limit: 50 })
  const unread = countUnreadNotifications()
  return NextResponse.json({ notifications, unread })
}
