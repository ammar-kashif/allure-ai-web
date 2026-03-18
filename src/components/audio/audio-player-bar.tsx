"use client"

import { useCallback, useEffect, useRef } from "react"
import { Pause, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { SpeedSelector } from "./speed-selector"
import { useAudioPlayback } from "@/stores/audio-playback"

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, "0")}`
}

interface AudioPlayerBarProps {
  recordingId: string
}

export function AudioPlayerBar({ recordingId }: AudioPlayerBarProps) {
  const audioRef = useRef<HTMLAudioElement>(null)

  const isPlaying = useAudioPlayback((s) => s.isPlaying)
  const currentTime = useAudioPlayback((s) => s.currentTime)
  const duration = useAudioPlayback((s) => s.duration)
  const playbackRate = useAudioPlayback((s) => s.playbackRate)

  const play = useAudioPlayback((s) => s.play)
  const pause = useAudioPlayback((s) => s.pause)
  const togglePlayback = useAudioPlayback((s) => s.togglePlayback)
  const seek = useAudioPlayback((s) => s.seek)
  const setPlaybackRate = useAudioPlayback((s) => s.setPlaybackRate)
  const setCurrentTime = useAudioPlayback((s) => s.setCurrentTime)
  const setDuration = useAudioPlayback((s) => s.setDuration)
  const reset = useAudioPlayback((s) => s.reset)

  const audioSrc = `/api/recordings/${recordingId}/audio`

  // Sync isPlaying state to audio element
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.play().catch(() => {
        // Browser may block autoplay; revert state
        pause()
      })
    } else {
      audio.pause()
    }
  }, [isPlaying, pause])

  // Sync playbackRate to audio element
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.playbackRate = playbackRate
  }, [playbackRate])

  // Handle audio element events
  const handleLoadedMetadata = useCallback(() => {
    const audio = audioRef.current
    if (audio) setDuration(audio.duration)
  }, [setDuration])

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (audio) setCurrentTime(audio.currentTime)
  }, [setCurrentTime])

  const handleEnded = useCallback(() => {
    pause()
    seek(0)
  }, [pause, seek])

  // Handle seek from slider
  const handleSeek = useCallback(
    (value: number | readonly number[]) => {
      const time = Array.isArray(value) ? value[0] : value
      const audio = audioRef.current
      if (audio) {
        audio.currentTime = time
      }
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

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t bg-card shadow-[var(--shadow-card)]">
      <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-3">
        {/* Play / Pause */}
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

        {/* Current time */}
        <span className="w-11 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
          {formatTime(currentTime)}
        </span>

        {/* Seek slider */}
        <Slider
          className="flex-1"
          value={[currentTime]}
          min={0}
          max={duration || 1}
          step={0.1}
          onValueChange={handleSeek}
          aria-label="Seek"
        />

        {/* Duration */}
        <span className="w-11 shrink-0 text-xs tabular-nums text-muted-foreground">
          {formatTime(duration)}
        </span>

        {/* Speed selector */}
        <SpeedSelector value={playbackRate} onChange={setPlaybackRate} />
      </div>

      {/* Hidden audio element */}
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
}
