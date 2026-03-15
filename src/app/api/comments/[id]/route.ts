import { NextRequest, NextResponse } from "next/server"
import { deleteComment } from "@/lib/db/comments"

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const deleted = deleteComment(id)
  if (!deleted) return NextResponse.json({ error: "Not found" }, { status: 404 })
  return new NextResponse(null, { status: 204 })
}
