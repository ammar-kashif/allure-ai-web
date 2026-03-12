"use client"

import { useEffect, useRef, useCallback } from "react"
import { UtteranceBubble } from "@/components/transcript/utterance-bubble"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import type { Transcript } from "@/types/recording"

interface TranscriptViewProps {
  transcript: Transcript
}

export function TranscriptView({ transcript }: TranscriptViewProps) {
  const highlightIndex = useEvidenceHighlight((s) => s.highlightUtteranceIndex)
  const containerRef = useRef<HTMLDivElement>(null)

  // Scroll to highlighted utterance when it changes
  useEffect(() => {
    if (highlightIndex === null || !containerRef.current) return

    const el = containerRef.current.querySelector(
      `[data-utterance-index="${highlightIndex}"]`
    )
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [highlightIndex])

  if (!transcript.utterances || transcript.utterances.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        No transcript content available
      </div>
    )
  }

  const utterances = transcript.utterances

  return (
    <div ref={containerRef} className="space-y-1">
      {utterances.map((utterance, index) => {
        const prevSpeaker =
          index > 0 ? utterances[index - 1].speaker : null
        const isSameSpeaker = utterance.speaker === prevSpeaker
        const isHighlighted = highlightIndex === index

        return (
          <div
            key={utterance.id}
            data-utterance-index={index}
            className={isSameSpeaker ? "mt-1" : "mt-3 first:mt-0"}
          >
            <UtteranceBubble
              utterance={utterance}
              showSpeaker={!isSameSpeaker}
              highlighted={isHighlighted}
            />
          </div>
        )
      })}
    </div>
  )
}
