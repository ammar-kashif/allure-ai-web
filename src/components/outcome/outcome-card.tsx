"use client"

import { useState } from "react"
import { ExternalLink, Check, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { usePromoteOutcome } from "@/hooks/use-outcomes"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import type { Outcome, EvidenceRef } from "@/types/outcome"
import { cn, formatTimecode } from "@/lib/utils"

interface OutcomeCardProps {
  outcome: Outcome
  recordingId: string
  outcomeIndex: number
}

export function OutcomeCard({
  outcome,
  recordingId,
  outcomeIndex,
}: OutcomeCardProps) {
  const [showAllRefs, setShowAllRefs] = useState(false)
  const promote = usePromoteOutcome()
  const setHighlight = useEvidenceHighlight((s) => s.setHighlight)

  const isHighConfidence = outcome.confidence >= 0.8
  const canPromote =
    outcome.type === "action_item" || outcome.type === "requirement"
  const isPromoted = outcome.promoted

  const handlePromote = () => {
    promote.mutate(
      {
        outcomeId: outcome.id,
        recordingId,
        outcomeIndex,
      },
      {
        onSuccess: () => {
          const label =
            outcome.type === "action_item" ? "Task created" : "Requirement created"
          toast.success(label)
        },
        onError: () => {
          toast.error("Failed to promote outcome")
        },
      }
    )
  }

  const handleEvidenceClick = (ref: EvidenceRef) => {
    setHighlight(ref.segmentIndex)
  }

  const primaryRef = outcome.evidenceRefs[0]
  const extraRefs = outcome.evidenceRefs.slice(1)

  return (
    <div className="rounded-xl border border-border/70 bg-card p-5 shadow-[var(--shadow-card)] transition-[box-shadow,transform] duration-[var(--duration-normal)] ease-[var(--ease-out)] hover:shadow-[var(--shadow-card-hover)] hover:-translate-y-px">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <h4 className="text-title line-clamp-1">{outcome.title}</h4>
          <p className="text-label text-muted-foreground line-clamp-2">
            {outcome.detail}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium font-numeric",
              isHighConfidence
                ? "border-border/70 text-foreground"
                : "border-border/70 text-muted-foreground"
            )}
          >
            <span className={cn(
              "inline-flex h-1.5 w-1.5 rounded-full",
              isHighConfidence ? "bg-foreground/70" : "border border-foreground/50"
            )} />
            {outcome.confidence.toFixed(2)}
          </span>
          {!isHighConfidence && (
            <span className="text-xs font-medium text-muted-foreground">
              Needs review
            </span>
          )}
        </div>
      </div>

      {/* Evidence references */}
      {primaryRef && (
        <div className="mt-3 space-y-1">
          <EvidenceLink ref_={primaryRef} onClick={handleEvidenceClick} />
          {extraRefs.length > 0 && !showAllRefs && (
            <button
              type="button"
              onClick={() => setShowAllRefs(true)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              +{extraRefs.length} more
            </button>
          )}
          {showAllRefs &&
            extraRefs.map((ref, i) => (
              <EvidenceLink
                key={i}
                ref_={ref}
                onClick={handleEvidenceClick}
              />
            ))}
        </div>
      )}

      {/* Promote / Promoted */}
      {canPromote && (
        <div className="mt-3">
          {isPromoted ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
              <Check className="size-3.5" />
              Promoted
            </span>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handlePromote}
              disabled={promote.isPending}
            >
              {promote.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : null}
              Promote
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function EvidenceLink({
  ref_,
  onClick,
}: {
  ref_: EvidenceRef
  onClick: (ref: EvidenceRef) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(ref_)}
      className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 hover:underline"
    >
      <ExternalLink className="size-3" />
      <span>
        <span className="font-numeric">{formatTimecode(ref_.timestamp)}</span>
        <span aria-hidden> · </span>
        {ref_.speaker}
      </span>
    </button>
  )
}

