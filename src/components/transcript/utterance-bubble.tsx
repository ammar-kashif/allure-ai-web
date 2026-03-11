"use client"

import { cn } from "@/lib/utils"
import type { Utterance } from "@/types/recording"

const speakerColors = [
  { bg: "bg-blue-50", label: "text-blue-700" },
  { bg: "bg-emerald-50", label: "text-emerald-700" },
  { bg: "bg-purple-50", label: "text-purple-700" },
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
}

export function UtteranceBubble({
  utterance,
  showSpeaker = true,
}: UtteranceBubbleProps) {
  const colorIndex = getSpeakerIndex(utterance.speaker)
  const colors = speakerColors[colorIndex]

  return (
    <div className={cn("max-w-[85%] rounded-lg px-4 py-3", colors.bg)}>
      {showSpeaker && (
        <div className="mb-1 flex items-center gap-2">
          <span className={cn("text-xs font-semibold", colors.label)}>
            {utterance.speaker}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatTime(utterance.startTime)}
          </span>
        </div>
      )}
      {!showSpeaker && (
        <div className="mb-1">
          <span className="text-xs text-muted-foreground">
            {formatTime(utterance.startTime)}
          </span>
        </div>
      )}
      <p className="text-sm">{utterance.text}</p>
    </div>
  )
}
