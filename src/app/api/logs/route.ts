import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

const ALLOWED_PARAMS = [
  "limit",
  "category",
  "status",
  "recording_id",
  "job_id",
  "dispatch_id",
]

export async function GET(request: NextRequest) {
  const params = new URLSearchParams()
  for (const key of ALLOWED_PARAMS) {
    const value = request.nextUrl.searchParams.get(key)
    if (value) params.set(key, value)
  }

  const query = params.toString()
  const url = `${BACKEND_URL}/logs${query ? `?${query}` : ""}`

  try {
    const response = await fetch(url)
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
