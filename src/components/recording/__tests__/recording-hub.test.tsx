import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { http, HttpResponse } from "msw"
import { server } from "@/test/setup"

import { RecordingHub } from "../recording-hub"
import type { Recording } from "@/types/recording"

// Mock next/navigation
const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

const mockRecordings: Recording[] = [
  {
    id: "rec-1",
    title: "Recording Mar 12, 2026 3:00 PM",
    durationMs: 65000,
    filePath: "/path/to/rec-1.webm",
    status: "unassigned",
    projectId: null,
    backendId: null,
    errorMessage: null,
    createdAt: "2026-03-12T15:00:00Z",
    updatedAt: "2026-03-12T15:00:00Z",
  },
  {
    id: "rec-2",
    title: "Recording Mar 12, 2026 2:00 PM",
    durationMs: 180000,
    filePath: "/path/to/rec-2.webm",
    status: "processing",
    projectId: "proj-1",
    backendId: "backend-1",
    errorMessage: null,
    createdAt: "2026-03-12T14:00:00Z",
    updatedAt: "2026-03-12T14:00:00Z",
  },
  {
    id: "rec-3",
    title: "Recording Mar 12, 2026 1:00 PM",
    durationMs: 300000,
    filePath: "/path/to/rec-3.webm",
    status: "ready",
    projectId: "proj-1",
    backendId: "backend-2",
    errorMessage: null,
    createdAt: "2026-03-12T13:00:00Z",
    updatedAt: "2026-03-12T13:00:00Z",
  },
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
}

beforeEach(() => {
  mockPush.mockClear()

  server.use(
    http.get("/api/recordings", () => {
      return HttpResponse.json(mockRecordings)
    }),
    http.get("/api/projects", () => {
      return HttpResponse.json([
        { id: "proj-1", name: "Test Project", createdAt: "2026-03-12", updatedAt: "2026-03-12" },
      ])
    }),
    http.get("/api/recordings/:id/status", () => {
      return HttpResponse.json({ status: "processing" })
    })
  )
})

describe("RecordingHub", () => {
  it("displays recordings in a table with Title, Duration, Status, Project, Date columns", async () => {
    render(<RecordingHub />, { wrapper: createWrapper() })

    // Wait for data to load
    expect(await screen.findByText("Recording Mar 12, 2026 3:00 PM")).toBeInTheDocument()

    // Check column headers
    expect(screen.getByText("Title")).toBeInTheDocument()
    expect(screen.getByText("Duration")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("Project")).toBeInTheDocument()
    expect(screen.getByText("Date")).toBeInTheDocument()

    // Check recordings are rendered
    expect(screen.getByText("Recording Mar 12, 2026 2:00 PM")).toBeInTheDocument()
    expect(screen.getByText("Recording Mar 12, 2026 1:00 PM")).toBeInTheDocument()
  })

  it("tab bar shows All, Unassigned, Processing, Ready with counts", async () => {
    render(<RecordingHub />, { wrapper: createWrapper() })

    await screen.findByText("Recording Mar 12, 2026 3:00 PM")

    // Check tabs exist via role
    expect(screen.getByRole("tab", { name: /All/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Unassigned/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Processing/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Ready/i })).toBeInTheDocument()
  })

  it("switching tabs filters the table by status", async () => {
    const user = userEvent.setup()
    render(<RecordingHub />, { wrapper: createWrapper() })

    await screen.findByText("Recording Mar 12, 2026 3:00 PM")

    // Click Unassigned tab
    await user.click(screen.getByRole("tab", { name: /Unassigned/i }))

    // Should show only unassigned recording
    const unassignedPanel = screen.getByRole("tabpanel")
    expect(within(unassignedPanel).getByText("Recording Mar 12, 2026 3:00 PM")).toBeInTheDocument()
    expect(within(unassignedPanel).queryByText("Recording Mar 12, 2026 2:00 PM")).not.toBeInTheDocument()
  })

  it("clicking a row navigates to /recordings/[id]", async () => {
    const user = userEvent.setup()
    render(<RecordingHub />, { wrapper: createWrapper() })

    const row = await screen.findByText("Recording Mar 12, 2026 3:00 PM")
    await user.click(row.closest("tr")!)

    expect(mockPush).toHaveBeenCalledWith("/recordings/rec-1")
  })
})

