import { NextRequest, NextResponse } from "next/server"
import { removeTaskDependency } from "@/lib/db/milestones"

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; blockerId: string }> }
) {
  const { id, blockerId } = await params
  removeTaskDependency(blockerId, id)
  return new NextResponse(null, { status: 204 })
}
