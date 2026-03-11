import Link from "next/link"

export default function DashboardPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20">
      <h2 className="text-2xl font-semibold tracking-tight">
        Welcome to Allure
      </h2>
      <p className="max-w-md text-center text-muted-foreground">
        Record meetings, transcribe conversations, and extract actionable
        insights -- all in one place.
      </p>
      <Link
        href="/recordings"
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Go to Recordings
      </Link>
    </div>
  )
}
