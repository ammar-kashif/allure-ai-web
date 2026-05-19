import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

interface DispatchRequest {
  meeting_url: string
  platform?: "google" | "microsoft" | "zoom"
  project_id?: string | null
  title?: string | null
}

export async function POST(request: NextRequest) {
  const body: DispatchRequest = await request.json()

  if (!body.meeting_url) {
    return NextResponse.json(
      { error: "meeting_url is required" },
      { status: 400 }
    )
  }

  try {
    const response = await fetch(`${BACKEND_URL}/meetings/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    const text = await response.text()
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
