"use client"

import { cn } from "@/lib/utils"
import type { Utterance } from "@/types/recording"

const speakerColors = [
  { bg: "bg-indigo-50", label: "text-indigo-700" },
  { bg: "bg-teal-50", label: "text-teal-700" },
  { bg: "bg-violet-50", label: "text-violet-700" },
  { bg: "bg-amber-50", label: "text-amber-700" },
  { bg: "bg-rose-50", label: "text-rose-700" },
] as const

function getSpeakerIndex(speaker: string): number {
  const match = speaker.match(/(\d+)/)
  if (match) {
    return (parseInt(match[1], 10) - 1) % speakerColors.length
  }
  return 0
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, "0")}`
}

interface UtteranceBubbleProps {
  utterance: Utterance
  showSpeaker?: boolean
  highlighted?: boolean
}

export function UtteranceBubble({
  utterance,
  showSpeaker = true,
  highlighted = false,
}: UtteranceBubbleProps) {
  const colorIndex = getSpeakerIndex(utterance.speaker)
  const colors = speakerColors[colorIndex]

  return (
    <div
      className={cn(
        "max-w-[85%] rounded-xl px-4 py-3 transition-[background-color] duration-1000 ease-[var(--ease-out)]",
        highlighted ? "bg-yellow-200/60" : colors.bg
      )}
    >
      <div className={cn("mb-1", showSpeaker && "flex items-center gap-2")}>
        {showSpeaker && (
          <span className={cn("text-xs font-semibold", colors.label)}>
            {utterance.speaker}
          </span>
        )}
        <span className="text-xs text-muted-foreground">
          {formatTime(utterance.startTime)}
        </span>
      </div>
      <p className="text-[0.9375rem] leading-relaxed">{utterance.text}</p>
    </div>
  )
}
