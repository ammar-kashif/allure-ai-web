import { cn } from "@/lib/utils"
import { speakerColors, getSpeakerIndex } from "./utterance-bubble"

interface SpeakerBadgeProps {
  speaker: string
  displayName?: string
  className?: string
}

export function SpeakerBadge({ speaker, displayName, className }: SpeakerBadgeProps) {
  const colorIndex = getSpeakerIndex(speaker)
  const colors = speakerColors[colorIndex]
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        colors.badge,
        className
      )}
    >
      {displayName || speaker}
    </span>
  )
}

