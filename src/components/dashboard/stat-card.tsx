import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  title: string
  value: number
  icon: LucideIcon
}

/**
 * Single stat cell. Renders as a column inside the dashboard stat strip.
 * Quiet by default: number leads, label sits beneath, icon is a small inline mark.
 * The 4-up hero-metric card grid was rejected in favor of this typography-led strip.
 */
export function StatCard({ title, value, icon: Icon }: StatCardProps) {
  return (
    <div className="flex flex-col gap-1.5 py-1">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
        <span className="text-label">{title}</span>
      </div>
      <p className="text-display font-semibold font-numeric leading-none">{value}</p>
    </div>
  )
}

