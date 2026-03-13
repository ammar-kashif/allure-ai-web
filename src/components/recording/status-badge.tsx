"use client"

import { Badge } from "@/components/ui/badge"
import type { RecordingStatus } from "@/types/recording"
import { cn } from "@/lib/utils"

const statusConfig: Record<
  RecordingStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
> = {
  unassigned: {
    label: "Unassigned",
    variant: "outline",
  },
  processing: {
    label: "Processing",
    variant: "secondary",
    className: "bg-primary/10 text-primary border-primary/20",
  },
  ready: {
    label: "Ready",
    variant: "default",
    className: "bg-emerald-600 text-white",
  },
  error: {
    label: "Error",
    variant: "destructive",
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
      className={cn(
        config.className,
        status === "processing" && "gap-1.5"
      )}
    >
      {status === "processing" && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
        </span>
      )}
      {config.label}
    </Badge>
  )
}
