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

const typeAccent: Record<OutcomeType, string> = {
  decision: "text-foreground/80 border-foreground/20",
  action_item: "text-foreground/80 border-foreground/20",
  requirement: "text-foreground/80 border-foreground/20",
  blocker: "text-destructive border-destructive/30",
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
        <CardTitle className="text-title">Recent Outcomes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topOutcomes.map((outcome) => (
          <Link
            key={outcome.id}
            href={`/recordings/${outcome.recordingId}`}
            className="flex items-center justify-between rounded-lg p-3 transition-[background-color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:bg-muted/50 active:scale-[0.995]"
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-body font-medium">{outcome.title}</span>
              <Badge
                variant="outline"
                className={`w-fit text-xs ${typeAccent[outcome.type]}`}
              >
                {typeLabels[outcome.type]}
              </Badge>
            </div>
            <span
              className={`text-body font-medium font-numeric ${
                outcome.confidence >= 0.8 ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {Math.round(outcome.confidence * 100)}%
            </span>
          </Link>
        ))}
        <Link
          href="/recordings"
          className="mt-3 block text-center text-label text-primary transition-colors duration-[var(--duration-fast)] hover:text-primary/80"
        >
          View all recordings
        </Link>
      </CardContent>
    </Card>
  )
}
