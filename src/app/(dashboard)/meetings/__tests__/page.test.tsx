import { describe, it, expect, beforeEach, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { http, HttpResponse } from "msw"

import LogsPage from "../page"
import { server } from "@/test/setup"
import type { LogEvent } from "@/types/log"

const logs: LogEvent[] = [
  {
    id: "log-1",
    created_at: "2026-05-20T00:00:00.000Z",
    level: "info",
    category: "bot",
    event: "bot.dispatched",
    status: "done",
    message: "Bot dispatched to meeting",
    recording_id: "dispatch-1",
    job_id: null,
    dispatch_id: "dispatch-1",
    duration_ms: null,
    metadata: {},
  },
  {
    id: "log-2",
    created_at: "2026-05-20T00:00:01.000Z",
    level: "info",
    category: "transcription",
    event: "stt.moonshine",
    status: "done",
    message: "Completed stt moonshine",
    recording_id: null,
    job_id: "job-1",
    dispatch_id: null,
    duration_ms: 1250,
    metadata: {},
  },
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
}

describe("LogsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    server.use(
      http.get("/api/logs", () => HttpResponse.json(logs)),
      http.post("/api/meetings/:id/stop", () =>
        HttpResponse.json({ recording_id: "dispatch-1", bot_response: { ok: true } })
      )
    )
  })

  it("renders populated log rows", async () => {
    render(<LogsPage />, { wrapper: createWrapper() })

    expect(await screen.findByText("Bot Dispatched")).toBeInTheDocument()
    expect(screen.getByText("Stt Moonshine")).toBeInTheDocument()
    expect(screen.getByText("Bot dispatched to meeting")).toBeInTheDocument()
    expect(screen.getByText("1.3 s")).toBeInTheDocument()
  })

  it("filters logs by search text", async () => {
    const user = userEvent.setup()
    render(<LogsPage />, { wrapper: createWrapper() })

    await screen.findByText("Bot Dispatched")
    await user.type(screen.getByPlaceholderText("Search logs"), "moonshine")

    expect(screen.queryByText("Bot Dispatched")).not.toBeInTheDocument()
    expect(screen.getByText("Stt Moonshine")).toBeInTheDocument()
  })

  it("shows stop action for latest active bot row", async () => {
    const user = userEvent.setup()
    let stopCalled = false
    server.use(
      http.post("/api/meetings/:id/stop", () => {
        stopCalled = true
        return HttpResponse.json({
          recording_id: "dispatch-1",
          bot_response: { ok: true },
        })
      })
    )

    render(<LogsPage />, { wrapper: createWrapper() })

    await user.click(await screen.findByRole("button", { name: /stop/i }))

    await waitFor(() => {
      expect(stopCalled).toBe(true)
    })
  })
})
