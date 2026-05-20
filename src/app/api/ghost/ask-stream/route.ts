import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export const dynamic = "force-dynamic"

export async function POST(request: NextRequest) {
  const body = await request.json()
  try {
    const upstream = await fetch(`${BACKEND_URL}/ghost/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => "Upstream error")
      return NextResponse.json({ error: text }, { status: upstream.status })
    }
    // Pass the SSE stream straight through.
    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    })
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 })
  }
}
