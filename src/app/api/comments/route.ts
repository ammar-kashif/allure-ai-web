import { NextRequest, NextResponse } from "next/server"
import { listComments, createComment } from "@/lib/db/comments"
import type { CommentEntityType } from "@/lib/db/comments"

export async function GET(request: NextRequest) {
  const entityType = request.nextUrl.searchParams.get("entityType") as CommentEntityType | null
  const entityId = request.nextUrl.searchParams.get("entityId")

  if (!entityType || !entityId) {
    return NextResponse.json({ error: "entityType and entityId are required" }, { status: 400 })
  }

  const comments = listComments(entityType, entityId)
  return NextResponse.json(comments)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { entityType, entityId, parentId, body: commentBody, authorName } = body

  if (!entityType || !entityId || !commentBody?.trim()) {
    return NextResponse.json({ error: "entityType, entityId, and body are required" }, { status: 400 })
  }

  const comment = createComment({
    entityType,
    entityId,
    parentId: parentId ?? null,
    body: commentBody.trim(),
    authorName: authorName ?? "User",
  })

  return NextResponse.json(comment, { status: 201 })
}
