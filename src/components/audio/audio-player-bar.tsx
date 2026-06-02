"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { Pause, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { SpeedSelector } from "./speed-selector"
import { useAudioPlayback } from "@/stores/audio-playback"
import { formatTimecode } from "@/lib/utils"
import type { Utterance } from "@/types/recording"

function findActiveUtterance(
  utterances: Utterance[],
  currentTime: number
): number | null {
  let low = 0
  let high = utterances.length - 1
  while (low <= high) {
    const mid = Math.floor((low + high) / 2)
    const u = utterances[mid]
    if (currentTime >= u.startTime && currentTime < u.endTime) return mid
    if (currentTime < u.startTime) high = mid - 1
    else low = mid + 1
  }
  return null
}

interface AudioPlayerBarProps {
  recordingId: string
  utterances?: Utterance[]
}

export function AudioPlayerBar({ recordingId, utterances }: AudioPlayerBarProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null)

  const isPlaying = useAudioPlayback((s) => s.isPlaying)
  const currentTime = useAudioPlayback((s) => s.currentTime)
  const duration = useAudioPlayback((s) => s.duration)
  const playbackRate = useAudioPlayback((s) => s.playbackRate)
  const seekGeneration = useAudioPlayback((s) => s.seekGeneration)

  const pause = useAudioPlayback((s) => s.pause)
  const togglePlayback = useAudioPlayback((s) => s.togglePlayback)
  const seek = useAudioPlayback((s) => s.seek)
  const setPlaybackRate = useAudioPlayback((s) => s.setPlaybackRate)
  const setCurrentTime = useAudioPlayback((s) => s.setCurrentTime)
  const setDuration = useAudioPlayback((s) => s.setDuration)
  const setActiveUtterance = useAudioPlayback((s) => s.setActiveUtterance)
  const reset = useAudioPlayback((s) => s.reset)

  // Resolve portal target on mount
  useEffect(() => {
    setPortalTarget(document.getElementById("player-portal"))
  }, [])

  const audioSrc = `/api/recordings/${recordingId}/audio`

  // Sync isPlaying state to audio element
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.play().catch(() => {
        pause()
      })
    } else {
      audio.pause()
    }
  }, [isPlaying, pause])

  // Sync seek intent to audio element
  const lastSyncedGeneration = useRef(0)
  useEffect(() => {
    if (seekGeneration === lastSyncedGeneration.current) return
    lastSyncedGeneration.current = seekGeneration
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = currentTime
    }
  }, [seekGeneration, currentTime])

  // Sync playbackRate to audio element
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.playbackRate = playbackRate
  }, [playbackRate])

  const handleLoadedMetadata = useCallback(() => {
    const audio = audioRef.current
    if (audio) setDuration(audio.duration)
  }, [setDuration])

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      setCurrentTime(audio.currentTime)
      if (utterances) {
        const idx = findActiveUtterance(utterances, audio.currentTime)
        setActiveUtterance(idx)
      }
    }
  }, [setCurrentTime, utterances, setActiveUtterance])

  const handleEnded = useCallback(() => {
    pause()
    seek(0)
  }, [pause, seek])

  const handleSliderSeek = useCallback(
    (value: number | readonly number[]) => {
      const time = Array.isArray(value) ? value[0] : value
      seek(time)
    },
    [seek]
  )

  // Clean up store on unmount
  useEffect(() => {
    return () => {
      reset()
    }
  }, [reset])

  const bar = (
    <div className="border-t bg-card shadow-[var(--shadow-card)]">
      <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={togglePlayback}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? (
            <Pause className="h-5 w-5" />
          ) : (
            <Play className="h-5 w-5" />
          )}
        </Button>

        <span className="w-11 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
          {formatTimecode(currentTime)}
        </span>

        <Slider
          className="flex-1"
          value={[currentTime]}
          min={0}
          max={duration || 1}
          step={0.1}
          onValueChange={handleSliderSeek}
          aria-label="Seek"
        />

        <span className="w-11 shrink-0 text-xs tabular-nums text-muted-foreground">
          {formatTimecode(duration)}
        </span>

        <SpeedSelector value={playbackRate} onChange={setPlaybackRate} />
      </div>

      <audio
        ref={audioRef}
        src={audioSrc}
        preload="metadata"
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
      />
    </div>
  )

  // Portal into #player-portal (inside SidebarInset, after <main>)
  if (portalTarget) {
    return createPortal(bar, portalTarget)
  }

  return null
}

