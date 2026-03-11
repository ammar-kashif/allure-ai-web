"use client"

import { UtteranceBubble } from "@/components/transcript/utterance-bubble"
import type { Transcript } from "@/types/recording"

interface TranscriptViewProps {
  transcript: Transcript
}

export function TranscriptView({ transcript }: TranscriptViewProps) {
  if (!transcript.utterances || transcript.utterances.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        No transcript content available
      </div>
    )
  }

  const utterances = transcript.utterances

  return (
    <div className="space-y-1">
      {utterances.map((utterance, index) => {
        const prevSpeaker =
          index > 0 ? utterances[index - 1].speaker : null
        const isSameSpeaker = utterance.speaker === prevSpeaker

        return (
          <div
            key={utterance.id}
            className={isSameSpeaker ? "mt-1" : "mt-3 first:mt-0"}
          >
            <UtteranceBubble
              utterance={utterance}
              showSpeaker={!isSameSpeaker}
            />
          </div>
        )
      })}
    </div>
  )
}
