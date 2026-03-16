"use client"

import { Badge } from "@/components/ui/badge"

const TYPE_CONFIG = {
  prd: { label: "PRD", className: "bg-primary/10 text-primary border-primary/20" },
  user_flow: { label: "User Flow", className: "bg-teal-500/10 text-teal-600 border-teal-500/20" },
  erd: { label: "ERD", className: "bg-violet-500/10 text-violet-600 border-violet-500/20" },
} as const

export function DocumentTypeBadge({ type }: { type: "prd" | "user_flow" | "erd" }) {
  const config = TYPE_CONFIG[type]
  return (
    <Badge className={config.className}>
      {config.label}
    </Badge>
  )
}
