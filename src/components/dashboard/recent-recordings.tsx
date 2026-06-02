import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/recording/status-badge"
import { formatDuration } from "@/lib/utils"
import type { Recording } from "@/types/recording"

interface RecentRecordingsProps {
  recordings: Recording[]
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diffMs = now - date
  const diffMinutes = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)

  if (diffMinutes < 1) return "just now"
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return new Date(dateStr).toLocaleDateString()
}

export function RecentRecordings({ recordings }: RecentRecordingsProps) {
  const recent = [...recordings]
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
    .slice(0, 5)

  if (recent.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-title">Recent Recordings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {recent.map((recording) => (
          <Link
            key={recording.id}
            href={`/recordings/${recording.id}`}
            className="flex items-center justify-between rounded-lg p-3 transition-[background-color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:bg-muted/50 active:scale-[0.995]"
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-body font-medium">{recording.title}</span>
              <span className="text-label text-muted-foreground font-numeric">
                {formatDuration(recording.durationMs)} &middot;{" "}
                {formatRelativeTime(recording.createdAt)}
              </span>
            </div>
            <StatusBadge status={recording.status} />
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

