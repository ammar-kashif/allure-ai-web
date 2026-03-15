import { NextRequest, NextResponse } from "next/server"
import { listActivity } from "@/lib/db/activity-log"

export async function GET(request: NextRequest) {
  const entityType = request.nextUrl.searchParams.get("entityType") ?? undefined
  const entityId = request.nextUrl.searchParams.get("entityId") ?? undefined
  const entries = listActivity({ entityType, entityId })
  return NextResponse.json(entries)
}
