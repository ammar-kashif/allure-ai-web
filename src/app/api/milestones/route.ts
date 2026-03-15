import { NextRequest, NextResponse } from "next/server"
import { listMilestones, createMilestone } from "@/lib/db/milestones"

export async function GET(request: NextRequest) {
  const projectId = request.nextUrl.searchParams.get("projectId") ?? undefined
  const milestones = listMilestones(projectId)
  return NextResponse.json(milestones)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { projectId, title, detail, startDate, endDate } = body

  if (!projectId || !title) {
    return NextResponse.json({ error: "projectId and title are required" }, { status: 400 })
  }

  const milestone = createMilestone({ projectId, title, detail, startDate, endDate })
  return NextResponse.json(milestone, { status: 201 })
}
