"use client"

import { Badge } from "@/components/ui/badge"
import type { RecordingStatus } from "@/types/recording"
import { cn } from "@/lib/utils"

const statusConfig: Record<
  RecordingStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string; dot?: "none" | "filled" | "pulse" }
> = {
  unassigned: {
    label: "Unassigned",
    variant: "outline",
    dot: "none",
  },
  processing: {
    label: "Processing",
    variant: "outline",
    className: "text-primary border-primary/30",
    dot: "pulse",
  },
  ready: {
    label: "Ready",
    variant: "outline",
    dot: "filled",
  },
  error: {
    label: "Error",
    variant: "destructive",
    dot: "none",
  },
}

interface StatusBadgeProps {
  status: RecordingStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status]

  return (
    <Badge
      variant={config.variant}
      className={cn(config.className, "gap-1.5")}
    >
      {config.dot === "pulse" && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {config.dot === "filled" && (
        <span className="inline-flex h-1.5 w-1.5 rounded-full bg-foreground/70" />
      )}
      {config.label}
    </Badge>
  )
}

