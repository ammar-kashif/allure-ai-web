"use client"

import { Clock, Paperclip, Timer, Users } from "lucide-react"
import { formatDuration } from "@/lib/utils"

interface MeetingStatCardsProps {
  duration?: number       // seconds
  processingTime?: number // seconds
  speakerCount?: number
  docCount?: number
}

export function MeetingStatCards({
  duration,
  processingTime,
  speakerCount,
  docCount,
}: MeetingStatCardsProps) {
  return (
    <div className="flex items-stretch gap-4">
      <StatCard
        icon={<Clock className="h-4 w-4 text-muted-foreground" />}
        label="Duration"
        value={duration != null ? formatDuration(duration * 1000) : "--"}
      />
      <StatCard
        icon={<Timer className="h-4 w-4 text-muted-foreground" />}
        label="Processing Time"
        value={processingTime != null ? formatDuration(processingTime * 1000) : "--"}
      />
      <StatCard
        icon={<Users className="h-4 w-4 text-muted-foreground" />}
        label="Speakers"
        value={speakerCount != null ? String(speakerCount) : "--"}
      />
      {docCount != null && (
        <StatCard
          icon={<Paperclip className="h-4 w-4 text-muted-foreground" />}
          label="Documents"
          value={String(docCount)}
        />
      )}
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex flex-1 items-center gap-3 rounded-xl bg-card p-4 shadow-[var(--shadow-card)]">
      {icon}
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-heading text-lg font-semibold tracking-[-0.01em]">
          {value}
        </p>
      </div>
    </div>
  )
}
