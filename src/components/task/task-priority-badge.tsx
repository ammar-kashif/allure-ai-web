"use client"

import { Badge } from "@/components/ui/badge"
import type { TaskPriority } from "@/types/outcome"

const priorityConfig: Record<
  TaskPriority,
  { label: string; className: string }
> = {
  high: { label: "High", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
  medium: { label: "Medium", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
  low: { label: "Low", className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" },
}

export function TaskPriorityBadge({ priority }: { priority: TaskPriority }) {
  const config = priorityConfig[priority]
  return (
    <Badge variant="secondary" className={config.className}>
      {config.label}
    </Badge>
  )
}
