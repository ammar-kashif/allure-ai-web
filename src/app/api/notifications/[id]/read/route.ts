import { NextRequest, NextResponse } from "next/server"
import { markNotificationRead } from "@/lib/db/notifications"

export async function PATCH(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  markNotificationRead(id)
  return NextResponse.json({ ok: true })
}
