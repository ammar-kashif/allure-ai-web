import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"

import { createDocument } from "@/lib/db/documents"

const generateDiagramSchema = z.object({
  type: z.enum(["user_flow", "erd"]),
})

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  const body = await request.json()
  const parsed = generateDiagramSchema.safeParse(body)

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Validation failed", details: parsed.error.issues },
      { status: 400 }
    )
  }

  try {
    const backendRes = await fetch(
      `http://localhost:8000/recordings/${id}/generate-diagram`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: parsed.data.type }),
      }
    )

    if (!backendRes.ok) {
      const errorText = await backendRes.text().catch(() => "Backend error")
      return NextResponse.json(
        { error: errorText },
        { status: backendRes.status }
      )
    }

    const data = await backendRes.json()

    const doc = createDocument({
      title: data.title,
      type: parsed.data.type,
      content: data.content,
      sourceRecordingId: id,
    })

    return NextResponse.json(doc, { status: 201 })
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 502 }
    )
  }
}
