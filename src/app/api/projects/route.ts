import { NextRequest, NextResponse } from "next/server"

import { getProjects, createProject } from "@/lib/db/projects"

export async function GET() {
  const projects = getProjects()
  return NextResponse.json(projects)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { name } = body

  if (!name || typeof name !== "string") {
    return NextResponse.json(
      { error: "Missing required field: name" },
      { status: 400 }
    )
  }

  const project = createProject(name.trim())
  return NextResponse.json(project, { status: 201 })
}

