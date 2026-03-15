"use client"

import { useState } from "react"
import { ExternalLink, Check, Loader2, FileText } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { usePromoteOutcome } from "@/hooks/use-outcomes"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import type { Outcome, EvidenceRef, SlideRef } from "@/types/outcome"
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

  const setActiveTab = useEvidenceHighlight((s) => s.setActiveTab)

  const handleEvidenceClick = (ref: EvidenceRef) => {
    setHighlight(ref.segmentIndex)
  }

  const handleSlideRefClick = () => {
    setActiveTab("documents")
  }

  const primaryRef = outcome.evidenceRefs[0]
  const extraRefs = outcome.evidenceRefs.slice(1)
  const slideRefs = outcome.slideRefs ?? []

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

      {/* Slide references */}
      {slideRefs.length > 0 && (
        <div className="mt-2 space-y-1">
          {slideRefs.map((ref, i) => (
            <SlideRefLink key={i} ref_={ref} onClick={handleSlideRefClick} />
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

function SlideRefLink({
  ref_,
  onClick,
}: {
  ref_: SlideRef
  onClick: () => void
}) {
  const label = ref_.slideTitle
    ? `Slide ${ref_.slideIndex + 1}: ${ref_.slideTitle}`
    : `Slide ${ref_.slideIndex + 1}`

  return (
    <div className="space-y-0.5">
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1 text-xs text-violet-600 hover:text-violet-500 hover:underline"
        title={ref_.relevance}
      >
        <FileText className="size-3 shrink-0" />
        <span className="truncate max-w-[240px]">
          {label} — {ref_.docFilename}
        </span>
      </button>
      {ref_.relevance && (
        <p className="ml-4 text-[11px] text-muted-foreground leading-snug line-clamp-1">
          {ref_.relevance}
        </p>
      )}
    </div>
  )
}
