"use client"

import {
  useRef,
  useState,
  useEffect,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react"
import { Pause, Play } from "lucide-react"

import { cn } from "@/lib/utils"
import type { Utterance } from "@/types/recording"

export interface AudioPlayerHandle {
  seekTo: (seconds: number) => void
}

interface AudioPlayerProps {
  audioUrl: string
  utterances: Utterance[]
  onCurrentUtteranceChange?: (index: number | null) => void
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return "0:00"
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, "0")}`
}

export const AudioPlayer = forwardRef<AudioPlayerHandle, AudioPlayerProps>(
  function AudioPlayer({ audioUrl, utterances, onCurrentUtteranceChange }, ref) {
    const audioRef = useRef<HTMLAudioElement>(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [isLoaded, setIsLoaded] = useState(false)

    const seekTo = useCallback((seconds: number) => {
      if (audioRef.current) {
        audioRef.current.currentTime = seconds
        audioRef.current.play().catch(() => {})
      }
    }, [])

    useImperativeHandle(ref, () => ({ seekTo }), [seekTo])

    const togglePlay = useCallback(() => {
      const audio = audioRef.current
      if (!audio) return
      if (isPlaying) {
        audio.pause()
      } else {
        audio.play().catch(() => {})
      }
    }, [isPlaying])

    // Sync currentTime → active utterance index
    useEffect(() => {
      if (!onCurrentUtteranceChange) return
      let idx: number | null = null
      for (let i = 0; i < utterances.length; i++) {
        if (
          currentTime >= utterances[i].startTime &&
          currentTime < utterances[i].endTime
        ) {
          idx = i
          break
        }
      }
      onCurrentUtteranceChange(idx)
    }, [currentTime, utterances, onCurrentUtteranceChange])

    const handleTimeUpdate = useCallback(() => {
      if (audioRef.current) setCurrentTime(audioRef.current.currentTime)
    }, [])

    const handleLoadedMetadata = useCallback(() => {
      if (audioRef.current) {
        setDuration(audioRef.current.duration)
        setIsLoaded(true)
      }
    }, [])

    const handleSeekBarChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        const t = parseFloat(e.target.value)
        if (audioRef.current) {
          audioRef.current.currentTime = t
          setCurrentTime(t)
        }
      },
      []
    )

    const progress = duration > 0 ? (currentTime / duration) * 100 : 0

    return (
      <div className="sticky top-0 z-10 rounded-xl border bg-card px-4 py-3 shadow-[var(--shadow-card)] space-y-2">
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />

        <div className="flex items-center gap-3">
          {/* Play / Pause */}
          <button
            onClick={togglePlay}
            disabled={!isLoaded}
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors",
              "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
            )}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5 translate-x-px" />
            )}
          </button>

          {/* Time */}
          <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
            {formatTime(currentTime)}
          </span>

          {/* Seek bar */}
          <div className="relative flex-1">
            {/* Track background */}
            <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-none"
                style={{ width: `${progress}%` }}
              />
            </div>
            {/* Invisible range input on top */}
            <input
              type="range"
              min={0}
              max={duration || 0}
              step={0.1}
              value={currentTime}
              onChange={handleSeekBarChange}
              disabled={!isLoaded}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              aria-label="Seek"
            />
          </div>

          {/* Duration */}
          <span className="w-10 shrink-0 text-xs tabular-nums text-muted-foreground">
            {formatTime(duration)}
          </span>
        </div>
      </div>
    )
  }
)
