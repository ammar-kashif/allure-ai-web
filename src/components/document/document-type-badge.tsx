"use client"

import { Badge } from "@/components/ui/badge"

const TYPE_LABEL = {
  prd: "PRD",
  user_flow: "User Flow",
  erd: "ERD",
} as const

export function DocumentTypeBadge({ type }: { type: "prd" | "user_flow" | "erd" }) {
  return (
    <Badge variant="outline" className="text-muted-foreground">
      {TYPE_LABEL[type]}
    </Badge>
  )
}

