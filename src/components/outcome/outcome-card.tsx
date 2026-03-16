"use client"

import { useState } from "react"
import { ExternalLink, Check, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { usePromoteOutcome } from "@/hooks/use-outcomes"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import type { Outcome, EvidenceRef } from "@/types/outcome"
import { cn } from "@/lib/utils"

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, "0")}`
}

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
    <div
      className={cn(
        "rounded-xl bg-card p-5 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-[box-shadow,transform] duration-[var(--duration-normal)] ease-[var(--ease-out)] hover:-translate-y-px border-l-4",
        isHighConfidence ? "border-l-green-500" : "border-l-amber-500"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <h4 className="font-semibold leading-tight tracking-[-0.01em] line-clamp-1">
            {outcome.title}
          </h4>
          <p className="text-[0.8125rem] leading-relaxed text-muted-foreground line-clamp-2">
            {outcome.detail}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
              isHighConfidence
                ? "bg-green-100 text-green-800"
                : "bg-amber-100 text-amber-800"
            )}
          >
            {outcome.confidence.toFixed(2)}
          </span>
          {!isHighConfidence && (
            <span className="text-xs font-medium text-amber-700">
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
            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
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
        {formatTimestamp(ref_.timestamp)} -- {ref_.speaker}
      </span>
    </button>
  )
}
