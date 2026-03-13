import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"

import { listTasks, createTask } from "@/lib/db/tasks"

const createTaskSchema = z.object({
  title: z.string().min(1),
  detail: z.string().optional(),
  priority: z.enum(["low", "medium", "high"]).optional(),
  dueDate: z.string().nullable().optional(),
  assignee: z.string().nullable().optional(),
  tags: z.array(z.string()).optional(),
})

export async function GET(request: NextRequest) {
  const status = request.nextUrl.searchParams.get("status")
  const search = request.nextUrl.searchParams.get("search")
  const tasks = listTasks({ status, search })
  return NextResponse.json(tasks)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const parsed = createTaskSchema.safeParse(body)

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Validation failed", details: parsed.error.issues },
      { status: 400 }
    )
  }

  const task = createTask(parsed.data)
  return NextResponse.json(task, { status: 201 })
}
