import { NextRequest, NextResponse } from "next/server"

import { listDocuments } from "@/lib/db/documents"

export async function GET(request: NextRequest) {
  const type = request.nextUrl.searchParams.get("type")
  const sourceRecordingId = request.nextUrl.searchParams.get("sourceRecordingId")
  const documents = listDocuments({ type, sourceRecordingId })
  return NextResponse.json(documents)
}

