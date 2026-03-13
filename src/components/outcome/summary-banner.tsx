"use client"

import {
  FileText,
  CheckSquare,
  Target,
  AlertTriangle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { Outcome, OutcomeType } from "@/types/outcome"

const typeConfig: Record<
  OutcomeType,
  { icon: React.ElementType; label: string }
> = {
  decision: { icon: FileText, label: "Decisions" },
  action_item: { icon: CheckSquare, label: "Actions" },
  requirement: { icon: Target, label: "Requirements" },
  blocker: { icon: AlertTriangle, label: "Blockers" },
}

interface SummaryBannerProps {
  outcomes: Outcome[]
}

export function SummaryBanner({ outcomes }: SummaryBannerProps) {
  const total = outcomes.length
  const needsReview = outcomes.filter((o) => o.confidence < 0.8).length

  const typeCounts = (
    Object.keys(typeConfig) as OutcomeType[]
  ).reduce(
    (acc, type) => {
      acc[type] = outcomes.filter((o) => o.type === type).length
      return acc
    },
    {} as Record<OutcomeType, number>
  )

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-primary/5 px-4 py-3">
      <div className="flex items-center gap-1.5">
        <span className="text-2xl font-heading font-bold">{total}</span>
        <span className="text-sm text-muted-foreground">outcomes</span>
      </div>

      <div className="h-6 w-px bg-border" />

      <div className="flex flex-wrap items-center gap-2">
        {(Object.keys(typeConfig) as OutcomeType[]).map((type) => {
          const count = typeCounts[type]
          if (count === 0) return null
          const { icon: Icon, label } = typeConfig[type]
          return (
            <Badge key={type} variant="secondary" className="gap-1">
              <Icon className="size-3" />
              <span>
                {count} {label}
              </span>
            </Badge>
          )
        })}
      </div>

      {needsReview > 0 && (
        <>
          <div className="h-6 w-px bg-border" />
          <Badge variant="outline" className="gap-1 border-amber-300 bg-amber-50 text-amber-800">
            <AlertTriangle className="size-3" />
            <span>Needs review: {needsReview}</span>
          </Badge>
        </>
      )}
    </div>
  )
}
