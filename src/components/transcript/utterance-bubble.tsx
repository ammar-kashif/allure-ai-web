"use client"

import { useCallback, useRef, useState } from "react"
import { Pencil, Check, X } from "lucide-react"

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
  speakerRole?: string
  showSpeaker?: boolean
  highlighted?: boolean
  isPlaying?: boolean
  onSeek?: (seconds: number) => void
  onRenameSpeaker?: (oldLabel: string, newLabel: string) => void
}

export function UtteranceBubble({
  utterance,
  speakerRole,
  showSpeaker = true,
  highlighted = false,
  isPlaying = false,
  onSeek,
  onRenameSpeaker,
}: UtteranceBubbleProps) {
  const colorIndex = getSpeakerIndex(utterance.speaker)
  const colors = speakerColors[colorIndex]

  const [isEditingSpeaker, setIsEditingSpeaker] = useState(false)
  const [speakerDraft, setSpeakerDraft] = useState(utterance.speaker)
  const inputRef = useRef<HTMLInputElement>(null)

  const startEdit = useCallback(() => {
    setSpeakerDraft(utterance.speaker)
    setIsEditingSpeaker(true)
    setTimeout(() => {
      inputRef.current?.focus()
      inputRef.current?.select()
    }, 0)
  }, [utterance.speaker])

  const confirmEdit = useCallback(() => {
    const trimmed = speakerDraft.trim()
    if (trimmed && trimmed !== utterance.speaker && onRenameSpeaker) {
      onRenameSpeaker(utterance.speaker, trimmed)
    }
    setIsEditingSpeaker(false)
  }, [speakerDraft, utterance.speaker, onRenameSpeaker])

  const cancelEdit = useCallback(() => {
    setSpeakerDraft(utterance.speaker)
    setIsEditingSpeaker(false)
  }, [utterance.speaker])

  return (
    <div
      className={cn(
        "group/bubble max-w-[85%] rounded-xl px-4 py-3 transition-[background-color] duration-1000 ease-[var(--ease-out)]",
        isPlaying
          ? "ring-2 ring-primary/40"
          : highlighted
          ? "bg-yellow-200/60"
          : colors.bg
      )}
    >
      {showSpeaker && (
        <div className="mb-1 flex items-center gap-2">
          {isEditingSpeaker ? (
            <>
              <input
                ref={inputRef}
                value={speakerDraft}
                onChange={(e) => setSpeakerDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") confirmEdit()
                  if (e.key === "Escape") cancelEdit()
                }}
                className={cn(
                  "w-32 rounded border bg-white/80 px-1.5 py-0.5 text-xs font-semibold outline-none",
                  colors.label
                )}
              />
              <button
                onClick={confirmEdit}
                className="rounded p-0.5 hover:bg-black/5"
                aria-label="Confirm speaker rename"
              >
                <Check className="h-3 w-3" />
              </button>
              <button
                onClick={cancelEdit}
                className="rounded p-0.5 hover:bg-black/5"
                aria-label="Cancel speaker rename"
              >
                <X className="h-3 w-3" />
              </button>
            </>
          ) : (
            <>
              <span className={cn("text-xs font-semibold", colors.label)}>
                {utterance.speaker}
              </span>
              {speakerRole && (
                <span className="rounded-full bg-black/5 px-1.5 py-0.5 text-[10px] text-muted-foreground font-medium">
                  {speakerRole}
                </span>
              )}
              {onRenameSpeaker && (
                <button
                  onClick={startEdit}
                  className="opacity-0 rounded p-0.5 transition-opacity hover:bg-black/5 group-hover/bubble:opacity-100"
                  aria-label={`Rename ${utterance.speaker}`}
                >
                  <Pencil className="h-2.5 w-2.5 text-muted-foreground" />
                </button>
              )}
            </>
          )}
          <button
            onClick={() => onSeek?.(utterance.startTime)}
            className={cn(
              "text-xs text-muted-foreground transition-colors",
              onSeek ? "cursor-pointer hover:text-foreground hover:underline" : "cursor-default"
            )}
            aria-label={`Seek to ${formatTime(utterance.startTime)}`}
          >
            {formatTime(utterance.startTime)}
          </button>
        </div>
      )}
      {!showSpeaker && (
        <div className="mb-1">
          <button
            onClick={() => onSeek?.(utterance.startTime)}
            className={cn(
              "text-xs text-muted-foreground transition-colors",
              onSeek ? "cursor-pointer hover:text-foreground hover:underline" : "cursor-default"
            )}
            aria-label={`Seek to ${formatTime(utterance.startTime)}`}
          >
            {formatTime(utterance.startTime)}
          </button>
        </div>
      )}
      <p className="text-[0.9375rem] leading-relaxed">{utterance.text}</p>
    </div>
  )
}
