import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

async function proxy(request: NextRequest, method: "GET" | "PATCH") {
  const init: RequestInit = { method }
  if (method === "PATCH") {
    init.headers = { "Content-Type": "application/json" }
    init.body = JSON.stringify(await request.json())
  }
  try {
    const response = await fetch(`${BACKEND_URL}/ghost/settings`, init)
    const text = await response.text()
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 })
  }
}

export async function GET(request: NextRequest) {
  return proxy(request, "GET")
}

export async function PATCH(request: NextRequest) {
  return proxy(request, "PATCH")
}
