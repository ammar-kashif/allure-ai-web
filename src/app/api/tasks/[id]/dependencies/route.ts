import { NextRequest, NextResponse } from "next/server"
import { addTaskDependency, getTaskDependencies } from "@/lib/db/milestones"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const deps = getTaskDependencies(id)
  return NextResponse.json(deps)
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const { blockerId } = await request.json()
  if (!blockerId) return NextResponse.json({ error: "blockerId required" }, { status: 400 })
  if (blockerId === id) return NextResponse.json({ error: "A task cannot depend on itself" }, { status: 400 })
  addTaskDependency(blockerId, id)
  return NextResponse.json({ ok: true })
}
