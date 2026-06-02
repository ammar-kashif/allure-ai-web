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

  const typeCounts: Record<OutcomeType, number> = {
    decision: 0,
    action_item: 0,
    requirement: 0,
    blocker: 0,
  }
  for (const o of outcomes) {
    typeCounts[o.type]++
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/70 bg-card px-5 py-3.5">
      <div className="flex items-center gap-1.5">
        <span className="text-headline font-numeric">{total}</span>
        <span className="text-label text-muted-foreground">outcomes</span>
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
          <Badge variant="outline" className="gap-1.5 text-muted-foreground">
            <AlertTriangle className="size-3" />
            <span>Needs review: <span className="font-numeric font-medium text-foreground">{needsReview}</span></span>
          </Badge>
        </>
      )}
    </div>
  )
}

