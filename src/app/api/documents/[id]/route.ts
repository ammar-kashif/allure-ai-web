import { NextRequest, NextResponse } from "next/server"

import { getDocument } from "@/lib/db/documents"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const document = getDocument(id)

  if (!document) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 })
  }

  return NextResponse.json(document)
}

