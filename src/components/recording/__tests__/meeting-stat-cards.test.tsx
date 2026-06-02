import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { MeetingStatCards } from "../meeting-stat-cards"

describe("MeetingStatCards", () => {
  it("renders 3 cards when no docCount provided", () => {
    render(
      <MeetingStatCards
        duration={120}
        processingTime={30}
        speakerCount={2}
      />
    )

    expect(screen.getByText("Duration")).toBeDefined()
    expect(screen.getByText("Processing Time")).toBeDefined()
    expect(screen.getByText("Speakers")).toBeDefined()
    expect(screen.queryByText("Documents")).toBeNull()
  })

  it("renders 4 cards when docCount is provided", () => {
    render(
      <MeetingStatCards
        duration={120}
        processingTime={30}
        speakerCount={2}
        docCount={3}
      />
    )

    expect(screen.getByText("Duration")).toBeDefined()
    expect(screen.getByText("Processing Time")).toBeDefined()
    expect(screen.getByText("Speakers")).toBeDefined()
    expect(screen.getByText("Documents")).toBeDefined()
  })

  it("shows the correct doc count value", () => {
    render(
      <MeetingStatCards
        duration={120}
        processingTime={30}
        speakerCount={2}
        docCount={5}
      />
    )

    expect(screen.getByText("5")).toBeDefined()
  })

  it("shows '0' when docCount is 0, not '--'", () => {
    render(
      <MeetingStatCards
        duration={120}
        processingTime={30}
        speakerCount={2}
        docCount={0}
      />
    )

    expect(screen.getByText("Documents")).toBeDefined()
    expect(screen.getByText("0")).toBeDefined()
  })
})

