"use client"

import { Badge } from "@/components/ui/badge"
import type { TaskPriority } from "@/types/outcome"

const priorityConfig: Record<
  TaskPriority,
  { label: string; dot: "filled" | "ring" | "none"; className?: string }
> = {
  high:   { label: "High",   dot: "filled", className: "text-foreground border-foreground/30" },
  medium: { label: "Medium", dot: "ring",   className: "text-foreground/80" },
  low:    { label: "Low",    dot: "none",   className: "text-muted-foreground" },
}

export function TaskPriorityBadge({ priority }: { priority: TaskPriority }) {
  const { label, dot, className } = priorityConfig[priority]
  return (
    <Badge variant="outline" className={`gap-1.5 ${className ?? ""}`}>
      {dot === "filled" && <span className="inline-flex h-1.5 w-1.5 rounded-full bg-foreground" />}
      {dot === "ring" && <span className="inline-flex h-1.5 w-1.5 rounded-full border border-foreground/60" />}
      {label}
    </Badge>
  )
}

