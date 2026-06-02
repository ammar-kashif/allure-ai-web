import Link from "next/link"
import { Mic } from "lucide-react"

export function DashboardEmptyState() {
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6 py-20 animate-fade-in-up">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Mic className="h-4 w-4" strokeWidth={1.75} />
        <span className="text-label">No recordings yet</span>
      </div>
      <h2 className="text-display">Record your first meeting.</h2>
      <p className="max-w-md text-body text-muted-foreground">
        Capture a conversation, get a transcript with speaker stats, then extract decisions,
        action items, and requirements. Generate a PRD when the meeting is done.
      </p>
      <div className="flex items-center gap-4 pt-2">
        <Link
          href="/recordings"
          className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-body font-medium text-primary-foreground transition-[background-color,box-shadow] duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:brightness-108 focus-visible:shadow-[var(--shadow-focus)]"
        >
          Go to recordings
        </Link>
        <span className="text-label text-muted-foreground">
          or use the mic in the lower right corner.
        </span>
      </div>
    </div>
  )
}

