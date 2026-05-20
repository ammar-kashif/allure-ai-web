"use client"

import { useQuery } from "@tanstack/react-query"

import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api/client"
import type { GhostCost } from "./types"

export function GhostCostBadge() {
  const { data } = useQuery({
    queryKey: ["ghost-cost"],
    queryFn: () => apiClient.get<GhostCost>("/api/ghost/cost"),
    refetchInterval: 30_000,
  })
  if (!data) return null
  const cap = data.monthly_cap_usd
  const spent = data.month_to_date_usd
  const ratio = cap > 0 ? spent / cap : 0
  const variant = ratio >= 1 ? "destructive" : ratio >= 0.8 ? "secondary" : "outline"
  return (
    <Badge variant={variant} title="Ghost spend this month">
      ${spent.toFixed(2)}
      {cap > 0 ? ` / $${cap.toFixed(2)}` : ""}
    </Badge>
  )
}
