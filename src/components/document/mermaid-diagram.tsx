"use client"

import { useEffect, useRef, useState } from "react"

function stripMermaidFences(raw: string): string {
  let s = raw.trim()
  if (s.startsWith("```")) {
    // Remove opening fence (```mermaid or ```)
    s = s.replace(/^```\w*\n?/, "")
    // Remove closing fence
    s = s.replace(/\n?```\s*$/, "")
  }
  return s.trim()
}

export function MermaidDiagram({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default
        mermaid.initialize({ startOnLoad: false, theme: "neutral" })

        const cleaned = stripMermaidFences(code)

        // Validate syntax first
        await mermaid.parse(cleaned)

        const { svg } = await mermaid.render(
          `mermaid-${crypto.randomUUID()}`,
          cleaned
        )

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err))
        }
      }
    }

    render()
    return () => {
      cancelled = true
    }
  }, [code])

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <p className="font-medium text-destructive">Diagram rendering error</p>
        <p className="mt-1 text-sm text-destructive/80">{error}</p>
        <pre className="mt-3 overflow-x-auto rounded bg-muted p-3 text-sm">
          {code}
        </pre>
      </div>
    )
  }

  return <div ref={containerRef} className="flex justify-center p-4" />
}
