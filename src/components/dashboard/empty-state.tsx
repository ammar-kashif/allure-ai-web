import Link from "next/link"
import { Mic } from "lucide-react"

export function DashboardEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20">
      <div className="rounded-2xl bg-primary/10 p-6">
        <Mic className="h-12 w-12 text-primary/60" />
      </div>
      <div className="text-center">
        <h2 className="text-2xl font-heading font-bold tracking-tight">
          Record your first meeting
        </h2>
        <p className="mt-2 max-w-md text-muted-foreground">
          Record a conversation, get it transcribed, extract decisions and action
          items, then review with confidence scores.
        </p>
      </div>
      <Link
        href="/recordings"
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Go to Recordings
      </Link>
      <p className="text-xs text-muted-foreground">
        Or click the microphone button in the bottom-right corner
      </p>
    </div>
  )
}
