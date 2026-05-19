import { describe, it, expect, vi, afterEach } from "vitest"
import { NextRequest } from "next/server"

import { GET } from "../route"

function createRequest(url: string): NextRequest {
  return new NextRequest(new URL(url, "http://localhost:3000"))
}

describe("logs API route", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("proxies allowed filters to the backend", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify([{ id: "log-1" }]), { status: 200 })
      )

    const request = createRequest(
      "http://localhost:3000/api/logs?category=bot&status=start&ignored=1"
    )
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([{ id: "log-1" }])
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/logs?category=bot&status=start"
    )
  })

  it("returns 503 when backend is unavailable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("down"))

    const response = await GET(createRequest("http://localhost:3000/api/logs"))
    const data = await response.json()

    expect(response.status).toBe(503)
    expect(data.error).toBe("Backend unavailable")
  })
})
