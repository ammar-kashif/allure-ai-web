import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { OutcomeCard } from "../outcome-card"
import type { Outcome } from "@/types/outcome"

vi.mock("@/hooks/use-outcomes", () => ({
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
    title: "Test Outcome",
    detail: "Some detail about this outcome",
    confidence: 0.92,
    evidenceRefs: [{ segmentIndex: 0, speaker: "Speaker 1", timestamp: 10 }],
    promoted: false,
    promotedId: null,
    ...overrides,
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

describe("OutcomeCard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders title, detail, confidence score for an outcome", () => {
    render(
      <OutcomeCard outcome={makeOutcome()} recordingId="r1" outcomeIndex={0} />,
      { wrapper }
    )

    expect(screen.getByText("Test Outcome")).toBeInTheDocument()
    expect(screen.getByText("Some detail about this outcome")).toBeInTheDocument()
    expect(screen.getByText("0.92")).toBeInTheDocument()
  })

  it("shows green confidence badge for score >= 0.80", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ confidence: 0.85 })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    const badge = screen.getByText("0.85")
    expect(badge.className).toMatch(/green/)
  })

  it("shows amber confidence badge with 'Needs review' for score < 0.80", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ confidence: 0.65 })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    const badge = screen.getByText("0.65")
    expect(badge.className).toMatch(/amber/)
    expect(screen.getByText("Needs review")).toBeInTheDocument()
  })

  it("shows amber left border for low-confidence items", () => {
    const { container } = render(
      <OutcomeCard
        outcome={makeOutcome({ confidence: 0.65 })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    const card = container.firstElementChild as HTMLElement
    expect(card.className).toMatch(/border-l.*amber|amber.*border-l|border-amber/)
  })

  it("shows Promote button for action_item type", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ type: "action_item" })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    expect(screen.getByRole("button", { name: /promote/i })).toBeInTheDocument()
  })

  it("shows Promote button for requirement type", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ type: "requirement" })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    expect(screen.getByRole("button", { name: /promote/i })).toBeInTheDocument()
  })

  it("does NOT show Promote button for decision type", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ type: "decision" })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    expect(screen.queryByRole("button", { name: /promote/i })).not.toBeInTheDocument()
  })

  it("does NOT show Promote button for blocker type", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({ type: "blocker" })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    expect(screen.queryByRole("button", { name: /promote/i })).not.toBeInTheDocument()
  })

  it("shows 'Promoted' badge instead of Promote when outcome.promoted is true", () => {
    render(
      <OutcomeCard
        outcome={makeOutcome({
          type: "action_item",
          promoted: true,
          promotedId: "t1",
        })}
        recordingId="r1"
        outcomeIndex={0}
      />,
      { wrapper }
    )

    expect(screen.queryByRole("button", { name: /promote/i })).not.toBeInTheDocument()
    expect(screen.getByText(/promoted/i)).toBeInTheDocument()
  })
})
