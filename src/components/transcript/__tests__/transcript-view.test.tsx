import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TranscriptView } from "../transcript-view"
import type { Transcript } from "@/types/recording"

function makeTranscript(utterances: Transcript["utterances"] = []): Transcript {
  return {
    id: "t1",
    recordingId: "r1",
    utterances,
  }
}

describe("TranscriptView", () => {
  it("renders utterance bubbles for each utterance", () => {
    const transcript = makeTranscript([
      { id: "u1", speaker: "Speaker 1", text: "Hello there.", startTime: 0, endTime: 3 },
      { id: "u2", speaker: "Speaker 2", text: "Hi, how are you?", startTime: 3, endTime: 6 },
    ])

    render(<TranscriptView transcript={transcript} />)

    expect(screen.getByText("Hello there.")).toBeInTheDocument()
    expect(screen.getByText("Hi, how are you?")).toBeInTheDocument()
  })

  it("displays formatted timestamps inline", () => {
    const transcript = makeTranscript([
      { id: "u1", speaker: "Speaker 1", text: "First line.", startTime: 92, endTime: 100 },
    ])

    render(<TranscriptView transcript={transcript} />)

    expect(screen.getByText("1:32")).toBeInTheDocument()
  })

  it("shows empty state when no utterances", () => {
    render(<TranscriptView transcript={makeTranscript()} />)

    expect(screen.getByText("No transcript content available")).toBeInTheDocument()
  })

  it("groups consecutive same-speaker utterances", () => {
    const transcript = makeTranscript([
      { id: "u1", speaker: "Speaker 1", text: "First line.", startTime: 0, endTime: 3 },
      { id: "u2", speaker: "Speaker 1", text: "Second line.", startTime: 3, endTime: 6 },
      { id: "u3", speaker: "Speaker 2", text: "Different speaker.", startTime: 6, endTime: 9 },
    ])

    render(<TranscriptView transcript={transcript} />)

    // Speaker 1 label should appear once (first utterance), not on the second
    const speaker1Labels = screen.getAllByText("Speaker 1")
    expect(speaker1Labels).toHaveLength(1)

    // Speaker 2 label should appear
    expect(screen.getByText("Speaker 2")).toBeInTheDocument()

    // All text should be visible
    expect(screen.getByText("First line.")).toBeInTheDocument()
    expect(screen.getByText("Second line.")).toBeInTheDocument()
    expect(screen.getByText("Different speaker.")).toBeInTheDocument()
  })
})
