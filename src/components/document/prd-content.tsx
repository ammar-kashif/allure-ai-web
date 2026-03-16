"use client"

interface PrdContentProps {
  content: string
}

export function PrdContent({ content }: PrdContentProps) {
  const lines = content.split("\n")

  return (
    <div className="rounded-xl bg-card p-6 shadow-[var(--shadow-card)] space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim()

        if (trimmed.startsWith("## ") || (trimmed.startsWith("**") && trimmed.endsWith("**"))) {
          const text = trimmed.replace(/^##\s*/, "").replace(/^\*\*|\*\*$/g, "")
          return (
            <h3
              key={i}
              className="font-heading font-semibold text-lg pt-4 first:pt-0"
            >
              {text}
            </h3>
          )
        }

        if (trimmed === "") {
          return <div key={i} className="h-2" />
        }

        return (
          <p key={i} className="text-base leading-relaxed text-foreground/90">
            {line}
          </p>
        )
      })}
    </div>
  )
}
