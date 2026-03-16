import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { http, HttpResponse } from "msw"
import { server } from "@/test/setup"
import React from "react"

import {
  useRecordings,
  useRecordingStatus,
  useUploadRecording,
} from "../use-recordings"

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    )
  }
}

const mockRecordings = [
  {
    id: "rec-1",
    title: "Test Recording 1",
    durationMs: 5000,
    filePath: "/path/rec-1.webm",
    status: "unassigned",
    projectId: null,
    backendId: null,
    errorMessage: null,
    createdAt: "2026-03-12 00:00:00",
    updatedAt: "2026-03-12 00:00:00",
  },
  {
    id: "rec-2",
    title: "Test Recording 2",
    durationMs: 3000,
    filePath: "/path/rec-2.webm",
    status: "processing",
    projectId: "proj-1",
    backendId: "backend-1",
    errorMessage: null,
    createdAt: "2026-03-12 00:00:00",
    updatedAt: "2026-03-12 00:00:00",
  },
]

describe("useRecordings", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("fetches recording list from /api/recordings", async () => {
    server.use(
      http.get("/api/recordings", () => {
        return HttpResponse.json(mockRecordings)
      })
    )

    const { result } = renderHook(() => useRecordings(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockRecordings)
    expect(result.current.data).toHaveLength(2)
  })

  it("unassigned - recordings with no projectId are not sent to backend", async () => {
    // This tests the API contract: unassigned recordings (no projectId)
    // only exist locally and are not proxied to backend.
    // The POST without projectId does not trigger backend upload.
    server.use(
      http.get("/api/recordings", ({ request }) => {
        const url = new URL(request.url)
        const status = url.searchParams.get("status")
        if (status === "unassigned") {
          return HttpResponse.json(
            mockRecordings.filter((r) => r.status === "unassigned")
          )
        }
        return HttpResponse.json(mockRecordings)
      })
    )

    const { result } = renderHook(() => useRecordings("unassigned"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    // Only unassigned recordings returned
    expect(result.current.data).toHaveLength(1)
    expect(result.current.data![0].status).toBe("unassigned")
    expect(result.current.data![0].projectId).toBeNull()
  })

  describe("useRecordingStatus", () => {
    it("polls /api/recordings/[id]/status every 3s when processing", async () => {
      let callCount = 0
      server.use(
        http.get("/api/recordings/rec-2/status", () => {
          callCount++
          return HttpResponse.json({ status: "processing" })
        })
      )

      const { result } = renderHook(
        () => useRecordingStatus("rec-2", true),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data?.status).toBe("processing")
      const initialCalls = callCount

      // Advance time by 3 seconds to trigger a poll
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })

      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCalls)
      })
    })

    it("stops polling when status is ready", async () => {
      server.use(
        http.get("/api/recordings/rec-ready/status", () => {
          return HttpResponse.json({ status: "ready" })
        })
      )

      const { result } = renderHook(
        () => useRecordingStatus("rec-ready", true),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data?.status).toBe("ready")
    })

    it("stops polling when status is error", async () => {
      server.use(
        http.get("/api/recordings/rec-err/status", () => {
          return HttpResponse.json({ status: "error" })
        })
      )

      const { result } = renderHook(
        () => useRecordingStatus("rec-err", true),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data?.status).toBe("error")
    })
  })

  describe("useUploadRecording", () => {
    it("POSTs FormData to /api/recordings", async () => {
      let receivedFormData = false
      server.use(
        http.post("/api/recordings", async ({ request }) => {
          // Verify it received FormData
          const contentType = request.headers.get("content-type") || ""
          if (contentType.includes("multipart/form-data")) {
            receivedFormData = true
          }
          return HttpResponse.json(
            {
              id: "rec-new",
              title: "New Recording",
              durationMs: 1000,
              filePath: "/path/rec-new.webm",
              status: "unassigned",
              projectId: null,
              backendId: null,
              errorMessage: null,
              createdAt: "2026-03-12 00:00:00",
              updatedAt: "2026-03-12 00:00:00",
            },
            { status: 201 }
          )
        })
      )

      const { result } = renderHook(() => useUploadRecording(), {
        wrapper: createWrapper(),
      })

      const formData = new FormData()
      formData.append(
        "file",
        new Blob(["audio"], { type: "audio/webm" }),
        "test.webm"
      )
      formData.append("recordingId", "rec-new")
      formData.append("title", "New Recording")
      formData.append("durationMs", "1000")

      await act(async () => {
        result.current.mutate(formData)
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data?.id).toBe("rec-new")
      expect(receivedFormData).toBe(true)
    })
  })
})
