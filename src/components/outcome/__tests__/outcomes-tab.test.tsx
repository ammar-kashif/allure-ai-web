import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { OutcomesTab } from "../outcomes-tab"
import type { OutcomesResponse, Outcome, ExtractionStatus } from "@/types/outcome"

// Mock the hooks
const mockUseOutcomes = vi.fn()
const mockUseExtractionStatus = vi.fn()

vi.mock("@/hooks/use-outcomes", () => ({
  useOutcomes: (...args: unknown[]) => mockUseOutcomes(...args),
  useExtractionStatus: (...args: unknown[]) => mockUseExtractionStatus(...args),
  usePromoteOutcome: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}))

vi.mock("@/stores/evidence-highlight", () => ({
  useEvidenceHighlight: Object.assign(
    vi.fn(() => ({
      setHighlight: vi.fn(),
      setActiveTab: vi.fn(),
    })),
    { getState: () => ({ setHighlight: vi.fn(), setActiveTab: vi.fn() }) }
  ),
}))

function makeOutcome(overrides: Partial<Outcome> = {}): Outcome {
  return {
    id: "o1",
    type: "decision",
    title: "Test Decision",
    detail: "Some detail about this outcome",
    confidence: 0.92,
    evidenceRefs: [{ segmentIndex: 0, speaker: "Speaker 1", timestamp: 10 }],
    promoted: false,
    promotedId: null,
    ...overrides,
  }
}

function makeOutcomesResponse(
  outcomes: Outcome[] = [],
  extractionStatus: ExtractionStatus = "completed"
): OutcomesResponse {
  return {
    jobId: "job-1",
    extractionStatus,
    outcomes,
  }
}

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe("OutcomesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseExtractionStatus.mockReturnValue({
      data: { extractionStatus: "completed" },
      isLoading: false,
    })
  })

  it("renders summary banner with correct counts when outcomes provided", () => {
    const outcomes = [
      makeOutcome({ id: "o1", type: "decision", confidence: 0.92 }),
      makeOutcome({ id: "o2", type: "action_item", confidence: 0.85 }),
      makeOutcome({ id: "o3", type: "action_item", confidence: 0.65 }),
      makeOutcome({ id: "o4", type: "blocker", confidence: 0.78 }),
    ]
    mockUseOutcomes.mockReturnValue({
      data: makeOutcomesResponse(outcomes),
      isLoading: false,
    })

    render(<OutcomesTab recordingId="r1" />, { wrapper })

    // Summary banner shows outcomes text and needs-review count
    expect(screen.getByText("outcomes")).toBeInTheDocument()
    expect(screen.getByText(/needs review: 2/i)).toBeInTheDocument()
  })

  it("shows skeleton loading state when extractionStatus is processing", () => {
    mockUseExtractionStatus.mockReturnValue({
      data: { extractionStatus: "processing" },
      isLoading: false,
    })
    mockUseOutcomes.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    render(<OutcomesTab recordingId="r1" />, { wrapper })

    // Skeleton loading cards should be present
    const skeletons = document.querySelectorAll(".animate-pulse")
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("shows error state when extractionStatus is failed", () => {
    mockUseExtractionStatus.mockReturnValue({
      data: { extractionStatus: "failed" },
      isLoading: false,
    })
    mockUseOutcomes.mockReturnValue({
      data: makeOutcomesResponse([], "failed"),
      isLoading: false,
    })

    render(<OutcomesTab recordingId="r1" />, { wrapper })

    expect(screen.getByText(/extraction failed/i)).toBeInTheDocument()
  })

  it("groups outcomes by type into collapsible sections", () => {
    const outcomes = [
      makeOutcome({ id: "o1", type: "decision", title: "Decision One" }),
      makeOutcome({ id: "o2", type: "action_item", title: "Action One" }),
      makeOutcome({ id: "o3", type: "requirement", title: "Req One" }),
    ]
    mockUseOutcomes.mockReturnValue({
      data: makeOutcomesResponse(outcomes),
      isLoading: false,
    })

    render(<OutcomesTab recordingId="r1" />, { wrapper })

    expect(screen.getByText("Decisions")).toBeInTheDocument()
    expect(screen.getByText("Action Items")).toBeInTheDocument()
    expect(screen.getByText("Requirements")).toBeInTheDocument()
    // Blockers section should not render since there are none
    expect(screen.queryByText("Blockers")).not.toBeInTheDocument()
  })

  it("shows 'No outcomes' message when outcomes array is empty and status is completed", () => {
    mockUseOutcomes.mockReturnValue({
      data: makeOutcomesResponse([], "completed"),
      isLoading: false,
    })

    render(<OutcomesTab recordingId="r1" />, { wrapper })

    expect(screen.getByText(/no outcomes extracted/i)).toBeInTheDocument()
  })
})
