import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

import { MermaidDiagram } from "./mermaid-diagram"

// Mock mermaid module
const mockParse = vi.fn()
const mockRender = vi.fn()
const mockInitialize = vi.fn()

vi.mock("mermaid", () => ({
  default: {
    initialize: (...args: unknown[]) => mockInitialize(...args),
    parse: (...args: unknown[]) => mockParse(...args),
    render: (...args: unknown[]) => mockRender(...args),
  },
}))

describe("MermaidDiagram component", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: parse succeeds, render returns SVG
    mockParse.mockResolvedValue(true)
    mockRender.mockResolvedValue({
      svg: '<svg data-testid="mermaid-svg"><text>Diagram</text></svg>',
    })
  })

  it("renders valid Mermaid code as SVG", async () => {
    const code = "flowchart TD\n  A[Start] --> B[End]"

    const { container } = render(<MermaidDiagram code={code} />)

    await waitFor(() => {
      expect(mockInitialize).toHaveBeenCalledWith({
        startOnLoad: false,
        theme: "neutral",
      })
    })

    await waitFor(() => {
      expect(mockParse).toHaveBeenCalledWith(code)
    })

    await waitFor(() => {
      expect(mockRender).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(container.querySelector("svg")).toBeTruthy()
    })
  })

  it("shows friendly message when code is not a diagram", () => {
    const code =
      "Based on the provided input, it seems there is a misunderstanding."

    render(<MermaidDiagram code={code} />)

    expect(screen.getByText("Diagram unavailable")).toBeInTheDocument()
    expect(
      screen.getByText(/didn't contain enough structured information/)
    ).toBeInTheDocument()
    expect(mockParse).not.toHaveBeenCalled()
  })

  it("shows syntax error fallback for invalid Mermaid syntax", async () => {
    const code = "flowchart TD\n  BAD SYNTAX {"
    mockParse.mockRejectedValue(new Error("Parse error: invalid syntax"))

    render(<MermaidDiagram code={code} />)

    await waitFor(() => {
      expect(
        screen.getByText("Diagram couldn't be rendered")
      ).toBeInTheDocument()
    })
  })

  it("displays raw code in fallback when parse fails", async () => {
    const code = "erDiagram\n  BAD SYNTAX"
    mockParse.mockRejectedValue(new Error("Unexpected token"))

    render(<MermaidDiagram code={code} />)

    await waitFor(() => {
      const preElement = document.querySelector("pre")
      expect(preElement).toBeTruthy()
      expect(preElement!.textContent).toBe(code)
    })
  })
})
