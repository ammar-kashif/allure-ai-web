import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { UtteranceBubble } from "../utterance-bubble"
import type { Utterance } from "@/types/recording"

function makeUtterance(overrides: Partial<Utterance> = {}): Utterance {
  return {
    id: "u1",
    speaker: "Speaker 1",
    text: "Hello, this is a test utterance.",
    startTime: 32,
    endTime: 45,
    ...overrides,
  }
}

describe("UtteranceBubble", () => {
  it("renders speaker label with correct color", () => {
    render(<UtteranceBubble utterance={makeUtterance()} />)

    const label = screen.getByText("Speaker 1")
    expect(label).toBeInTheDocument()
    expect(label.className).toContain("text-indigo-700")
  })

  it("renders utterance text", () => {
    render(<UtteranceBubble utterance={makeUtterance()} />)

    expect(screen.getByText("Hello, this is a test utterance.")).toBeInTheDocument()
  })

  it("renders timestamp formatted as M:SS", () => {
    render(<UtteranceBubble utterance={makeUtterance({ startTime: 32 })} />)

    expect(screen.getByText("0:32")).toBeInTheDocument()
  })

  it("formats multi-minute timestamps correctly", () => {
    render(<UtteranceBubble utterance={makeUtterance({ startTime: 125 })} />)

    expect(screen.getByText("2:05")).toBeInTheDocument()
  })

  it("cycles through 5 speaker colors", () => {
    const speakers = [
      { speaker: "Speaker 1", labelColor: "text-indigo-700", bgColor: "bg-indigo-50" },
      { speaker: "Speaker 2", labelColor: "text-teal-700", bgColor: "bg-teal-50" },
      { speaker: "Speaker 3", labelColor: "text-violet-700", bgColor: "bg-violet-50" },
      { speaker: "Speaker 4", labelColor: "text-amber-700", bgColor: "bg-amber-50" },
      { speaker: "Speaker 5", labelColor: "text-rose-700", bgColor: "bg-rose-50" },
    ]

    for (const { speaker, labelColor, bgColor } of speakers) {
      const { container, unmount } = render(
        <UtteranceBubble utterance={makeUtterance({ speaker })} />
      )

      const label = screen.getByText(speaker)
      expect(label.className).toContain(labelColor)

      const bubble = container.firstChild as HTMLElement
      expect(bubble.className).toContain(bgColor)

      unmount()
    }
  })

  it("wraps Speaker 6 back to first color (indigo)", () => {
    render(<UtteranceBubble utterance={makeUtterance({ speaker: "Speaker 6" })} />)

    const label = screen.getByText("Speaker 6")
    expect(label.className).toContain("text-indigo-700")
  })

  it("hides speaker label when showSpeaker is false", () => {
    render(<UtteranceBubble utterance={makeUtterance()} showSpeaker={false} />)

    expect(screen.queryByText("Speaker 1")).not.toBeInTheDocument()
    // Timestamp should still be visible
    expect(screen.getByText("0:32")).toBeInTheDocument()
  })
})

