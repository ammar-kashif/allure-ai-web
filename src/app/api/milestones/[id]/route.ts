import { NextRequest, NextResponse } from "next/server"
import { getMilestone, updateMilestone, deleteMilestone } from "@/lib/db/milestones"
import { listTasks } from "@/lib/db/tasks"

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const milestone = getMilestone(id)
  if (!milestone) return NextResponse.json({ error: "Not found" }, { status: 404 })
  const tasks = listTasks({ milestoneId: id })
  return NextResponse.json({ ...milestone, tasks })
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const body = await request.json()
  const milestone = updateMilestone(id, body)
  if (!milestone) return NextResponse.json({ error: "Not found" }, { status: 404 })
  return NextResponse.json(milestone)
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const deleted = deleteMilestone(id)
  if (!deleted) return NextResponse.json({ error: "Not found" }, { status: 404 })
  return new NextResponse(null, { status: 204 })
}
