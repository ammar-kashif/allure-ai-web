import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"

import { getTask, updateTask, deleteTask } from "@/lib/db/tasks"
import { logActivity } from "@/lib/db/activity-log"

const updateTaskSchema = z.object({
  title: z.string().min(1).optional(),
  detail: z.string().optional(),
  status: z.enum(["todo", "in_progress", "done"]).optional(),
  priority: z.enum(["low", "medium", "high"]).optional(),
  dueDate: z.string().nullable().optional(),
  assignee: z.string().nullable().optional(),
  tags: z.array(z.string()).optional(),
})

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const task = getTask(id)
  if (!task) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 })
  }
  return NextResponse.json(task)
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const body = await request.json()
  const parsed = updateTaskSchema.safeParse(body)

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Validation failed", details: parsed.error.issues },
      { status: 400 }
    )
  }

  const task = updateTask(id, parsed.data)
  if (!task) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 })
  }
  const changedFields = Object.keys(parsed.data).join(", ")
  logActivity({ action: "updated", entityType: "task", entityId: id, detail: changedFields })
  return NextResponse.json(task)
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const existing = getTask(id)
  const deleted = deleteTask(id)
  if (!deleted) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 })
  }
  logActivity({ action: "deleted", entityType: "task", entityId: id, detail: existing?.title ?? "" })
  return new NextResponse(null, { status: 204 })
}
