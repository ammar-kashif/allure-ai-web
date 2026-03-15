import Link from "next/link"
import { Mic } from "lucide-react"

export function DashboardEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-24 animate-fade-in-up">
      <div className="rounded-2xl bg-primary/8 p-7 shadow-[var(--shadow-sm)]">
        <Mic className="h-12 w-12 text-primary/60" />
      </div>
      <div className="text-center">
        <h2 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em]">
          Record your first meeting
        </h2>
        <p className="mt-3 max-w-md text-[0.9375rem] leading-relaxed text-muted-foreground">
          Record a conversation, get it transcribed, extract decisions and action
          items, then review with confidence scores.
        </p>
      </div>
      <Link
        href="/recordings"
        className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-6 text-[0.9375rem] font-medium text-primary-foreground shadow-[var(--shadow-xs)] transition-[transform,box-shadow,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:brightness-108 hover:shadow-[var(--shadow-sm)] hover:-translate-y-px active:scale-[0.98]"
      >
        Go to Recordings
      </Link>
      <p className="text-xs text-muted-foreground">
        Or click the microphone button in the bottom-right corner
      </p>
    </div>
  )
}
