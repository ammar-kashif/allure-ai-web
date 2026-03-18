"use client"

import { useCallback, useEffect, useRef } from "react"
import { ArrowDown } from "lucide-react"
import { UtteranceBubble } from "@/components/transcript/utterance-bubble"
import { Button } from "@/components/ui/button"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import { useAudioPlayback } from "@/stores/audio-playback"
import type { Transcript } from "@/types/recording"

interface TranscriptViewProps {
  transcript: Transcript
}

export function TranscriptView({ transcript }: TranscriptViewProps) {
  const highlightIndex = useEvidenceHighlight((s) => s.highlightUtteranceIndex)
  const containerRef = useRef<HTMLDivElement>(null)
  const isProgrammaticScroll = useRef(false)

  // Audio playback store
  const activeUtteranceIndex = useAudioPlayback((s) => s.activeUtteranceIndex)
  const isPlaying = useAudioPlayback((s) => s.isPlaying)
  const autoScrollEnabled = useAudioPlayback((s) => s.autoScrollEnabled)
  const seek = useAudioPlayback((s) => s.seek)
  const play = useAudioPlayback((s) => s.play)
  const disableAutoScroll = useAudioPlayback((s) => s.disableAutoScroll)
  const enableAutoScroll = useAudioPlayback((s) => s.enableAutoScroll)

  // Handle click-to-seek on utterance bubbles
  const handleSeek = useCallback(
    (startTime: number) => {
      seek(startTime)
      play()
    },
    [seek, play]
  )

  // Detect manual scroll to disable auto-scroll
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // We listen on the nearest scrollable ancestor (the page/window)
    const handleScroll = () => {
      if (isProgrammaticScroll.current) return
      if (isPlaying) {
        disableAutoScroll()
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [isPlaying, disableAutoScroll])

  // Auto-scroll to active utterance during playback
  useEffect(() => {
    if (
      activeUtteranceIndex === null ||
      !autoScrollEnabled ||
      !isPlaying ||
      !containerRef.current
    )
      return

    const el = containerRef.current.querySelector(
      `[data-utterance-index="${activeUtteranceIndex}"]`
    )
    if (el) {
      isProgrammaticScroll.current = true
      el.scrollIntoView({ behavior: "smooth", block: "center" })
      const timer = setTimeout(() => {
        isProgrammaticScroll.current = false
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [activeUtteranceIndex, autoScrollEnabled, isPlaying])

  // Scroll to highlighted utterance (evidence highlight from Outcomes tab)
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
    <div ref={containerRef} className="relative space-y-1">
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
              isPlaybackActive={activeUtteranceIndex === index}
              onSeek={handleSeek}
            />
          </div>
        )
      })}

      {/* Resume follow button -- shown when user scrolls away during playback */}
      {isPlaying && !autoScrollEnabled && (
        <div className="sticky bottom-24 z-40 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            className="shadow-md"
            onClick={enableAutoScroll}
          >
            <ArrowDown className="mr-1.5 h-3.5 w-3.5" />
            Resume follow
          </Button>
        </div>
      )}
    </div>
  )
}
