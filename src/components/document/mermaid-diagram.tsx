"use client"

import { useEffect, useRef, useState } from "react"
import { AlertTriangle } from "lucide-react"

const MERMAID_KEYWORDS =
  /^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitGraph|mindmap|timeline|sankey|xychart|block)/m

function stripMermaidFences(raw: string): string {
  let s = raw.trim()
  if (s.startsWith("```")) {
    s = s.replace(/^```\w*\n?/, "")
    s = s.replace(/\n?```\s*$/, "")
  }
  return s.trim()
}

function looksLikeDiagram(text: string): boolean {
  return MERMAID_KEYWORDS.test(text)
}

export function MermaidDiagram({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  const cleaned = stripMermaidFences(code)
  const isDiagram = looksLikeDiagram(cleaned)

  useEffect(() => {
    if (!isDiagram) return

    let cancelled = false

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default
        mermaid.initialize({ startOnLoad: false, theme: "neutral" })

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
  }, [cleaned, isDiagram])

  if (!isDiagram) {
    return (
      <div className="rounded-lg border border-border bg-muted/50 p-5 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-muted-foreground/60" />
        <p className="mt-3 font-medium text-foreground">
          Diagram unavailable
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          The meeting content didn&apos;t contain enough structured information
          to generate a diagram.
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-5 dark:border-amber-700 dark:bg-amber-950/30">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          <p className="font-medium text-amber-800 dark:text-amber-300">
            Diagram couldn&apos;t be rendered
          </p>
        </div>
        <p className="mt-1 text-sm text-amber-700 dark:text-amber-400/80">
          The generated diagram has a syntax issue. Raw content shown below.
        </p>
        <pre className="mt-3 overflow-x-auto rounded-md border border-amber-200 bg-white p-3 text-xs text-muted-foreground dark:border-amber-800 dark:bg-amber-950/50">
          {cleaned}
        </pre>
      </div>
    )
  }

  return <div ref={containerRef} className="flex justify-center p-4" />
}

