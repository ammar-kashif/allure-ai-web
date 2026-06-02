"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { SummaryBanner } from "@/components/outcome/summary-banner"
import { OutcomeSection } from "@/components/outcome/outcome-section"
import { OutcomeCard } from "@/components/outcome/outcome-card"
import { GenerateOutcomesButton } from "@/components/outcome/generate-outcomes-button"
import { useOutcomes, useExtractionStatus } from "@/hooks/use-outcomes"
import type { OutcomeType } from "@/types/outcome"

const sectionOrder: OutcomeType[] = [
  "decision",
  "action_item",
  "requirement",
  "blocker",
]

interface OutcomesTabProps {
  recordingId: string
}

export function OutcomesTab({ recordingId }: OutcomesTabProps) {
  const { data: outcomesData, isLoading: isOutcomesLoading } = useOutcomes(
    recordingId,
    true
  )
  const { data: statusData } = useExtractionStatus(recordingId, true)

  const extractionStatus =
    statusData?.extractionStatus ??
    outcomesData?.extractionStatus ??
    "none"

  // Loading / processing state
  if (
    extractionStatus === "pending" ||
    extractionStatus === "processing" ||
    isOutcomesLoading
  ) {
    return <OutcomesLoadingSkeleton />
  }

  // Not started state
  if (extractionStatus === "none") {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-muted-foreground">Extraction not started</p>
        <GenerateOutcomesButton recordingId={recordingId} />
      </div>
    )
  }

  // Error state
  if (extractionStatus === "failed") {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <p className="font-medium text-destructive">Extraction Failed</p>
        <p className="mt-1 text-sm text-destructive/80">
          AI extraction encountered an error. You can try re-running extraction.
        </p>
        <div className="mt-3">
          <GenerateOutcomesButton
            recordingId={recordingId}
            label="Retry Extraction"
          />
        </div>
      </div>
    )
  }

  const outcomes = outcomesData?.outcomes ?? []

  // Empty state
  if (extractionStatus === "completed" && outcomes.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        No outcomes extracted
      </div>
    )
  }

  // Completed with outcomes
  return (
    <div className="space-y-4">
      <SummaryBanner outcomes={outcomes} />

      {sectionOrder.map((type) => {
        const typeOutcomes = outcomes.filter((o) => o.type === type)
        if (typeOutcomes.length === 0) return null
        return (
          <OutcomeSection key={type} type={type} count={typeOutcomes.length}>
            {typeOutcomes.map((outcome) => (
              <OutcomeCard
                key={outcome.id}
                outcome={outcome}
                recordingId={recordingId}
                outcomeIndex={outcomes.indexOf(outcome)}
              />
            ))}
          </OutcomeSection>
        )
      })}
    </div>
  )
}

function OutcomesLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-14 w-full" />
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-24 w-full" />
        </div>
      ))}
    </div>
  )
}

