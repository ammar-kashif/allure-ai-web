"use client"

import { cn, formatTimecode } from "@/lib/utils"
import type { Utterance } from "@/types/recording"

export const speakerColors = [
  { bg: "bg-indigo-50", label: "text-indigo-700", badge: "bg-indigo-100 text-indigo-700" },
  { bg: "bg-teal-50", label: "text-teal-700", badge: "bg-teal-100 text-teal-700" },
  { bg: "bg-violet-50", label: "text-violet-700", badge: "bg-violet-100 text-violet-700" },
  { bg: "bg-amber-50", label: "text-amber-700", badge: "bg-amber-100 text-amber-700" },
  { bg: "bg-rose-50", label: "text-rose-700", badge: "bg-rose-100 text-rose-700" },
] as const

export function getSpeakerIndex(speaker: string): number {
  const match = speaker.match(/(\d+)/)
  if (match) {
    return (parseInt(match[1], 10) - 1) % speakerColors.length
  }
  return 0
}

interface UtteranceBubbleProps {
  utterance: Utterance
  showSpeaker?: boolean
  highlighted?: boolean
  isPlaybackActive?: boolean
  onSeek?: (startTime: number) => void
  displayName?: string
  role?: string
}

export function UtteranceBubble({
  utterance,
  showSpeaker = true,
  highlighted = false,
  isPlaybackActive = false,
  onSeek,
  displayName,
  role,
}: UtteranceBubbleProps) {
  const colorIndex = getSpeakerIndex(utterance.speaker)
  const colors = speakerColors[colorIndex]

  function getBgClass(): string {
    if (highlighted) return "bg-yellow-200/60"
    if (isPlaybackActive) return "bg-indigo-100/60"
    return colors.bg
  }

  return (
    <div
      className={cn(
        "max-w-[85%] rounded-xl px-4 py-3 transition-[background-color] duration-1000 ease-[var(--ease-out)]",
        getBgClass(),
        onSeek && "cursor-pointer"
      )}
      onClick={onSeek ? () => onSeek(utterance.startTime) : undefined}
    >
      <div className={cn("mb-1", showSpeaker && "flex items-center gap-2")}>
        {showSpeaker && (
          <span className={cn("text-xs font-semibold", colors.label)}>
            {displayName || utterance.speaker}
          </span>
        )}
        {role && (
          <span className="text-xs text-muted-foreground">{role}</span>
        )}
        <span className="text-xs text-muted-foreground font-numeric">
          {formatTimecode(utterance.startTime)}
        </span>
      </div>
      <p className="text-body">{utterance.text}</p>
    </div>
  )
}

