import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { Outcome, OutcomeType } from "@/types/outcome"

interface OutcomeWithRecording extends Outcome {
  recordingId: string
}

interface RecentOutcomesProps {
  outcomes: OutcomeWithRecording[]
}

const typeLabels: Record<OutcomeType, string> = {
  decision: "Decision",
  action_item: "Action Item",
  requirement: "Requirement",
  blocker: "Blocker",
}

const typeColors: Record<OutcomeType, string> = {
  decision: "bg-blue-100 text-blue-700",
  action_item: "bg-violet-100 text-violet-700",
  requirement: "bg-indigo-100 text-indigo-700",
  blocker: "bg-red-100 text-red-700",
}

export function RecentOutcomes({ outcomes }: RecentOutcomesProps) {
  // Show top 5 by confidence descending
  const topOutcomes = [...outcomes]
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5)

  if (topOutcomes.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-heading tracking-[-0.01em]">Recent Outcomes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topOutcomes.map((outcome) => (
          <Link
            key={outcome.id}
            href={`/recordings/${outcome.recordingId}`}
            className="flex items-center justify-between rounded-lg p-3 transition-[background-color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:bg-muted/50 active:scale-[0.995]"
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-base font-medium">{outcome.title}</span>
              <Badge
                variant="secondary"
                className={`w-fit text-xs ${typeColors[outcome.type]}`}
              >
                {typeLabels[outcome.type]}
              </Badge>
            </div>
            <span
              className={`text-base font-medium ${
                outcome.confidence >= 0.8
                  ? "text-green-600"
                  : "text-amber-600"
              }`}
            >
              {Math.round(outcome.confidence * 100)}%
            </span>
          </Link>
        ))}
        <Link
          href="/recordings"
          className="mt-3 block text-center text-[0.8125rem] font-medium text-primary transition-colors duration-[var(--duration-fast)] hover:text-primary/80"
        >
          View all recordings
        </Link>
      </CardContent>
    </Card>
  )
}
