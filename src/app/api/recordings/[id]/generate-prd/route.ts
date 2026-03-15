import { NextRequest, NextResponse } from "next/server"

import { createDocument } from "@/lib/db/documents"

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  try {
    const backendRes = await fetch(
      `http://localhost:8000/recordings/${id}/generate-prd`,
      { method: "POST" }
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
      type: "prd",
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
