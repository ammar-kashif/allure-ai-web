"use client"

import { useEffect, useState } from "react"
import { Mic, Square } from "lucide-react"

import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { formatDuration } from "@/lib/utils"
import { cn } from "@/lib/utils"
import {
  RecordingPrepareSheet,
  type AudioPayload,
} from "@/components/recording/recording-prepare-sheet"

export function RecordingFAB() {
  const { isRecording, elapsedSeconds, startRecording, stopRecording, onRecordingCompleteRef } =
    useAudioRecorder()

  const [pendingPayload, setPendingPayload] = useState<AudioPayload | null>(null)

  // When recording stops, capture the result and open the prepare sheet
  useEffect(() => {
    onRecordingCompleteRef.current = (result) => {
      setPendingPayload({
        file: result.blob,
        recordingId: result.recordingId,
        title: result.title,
        durationMs: result.durationMs,
        source: "record",
      })
    }

    return () => {
      onRecordingCompleteRef.current = null
    }
  }, [onRecordingCompleteRef])

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full transition-[transform,box-shadow,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]",
          "focus:outline-none focus-visible:shadow-[var(--shadow-focus)]",
          isRecording
            ? "animate-pulse bg-red-500 px-5 py-3 text-white shadow-[var(--shadow-lg)] hover:bg-red-600 hover:shadow-[var(--shadow-xl)] active:scale-95"
            : "bg-primary text-primary-foreground shadow-[var(--shadow-lg)] hover:shadow-[var(--shadow-xl)] hover:-translate-y-0.5 hover:brightness-110 active:scale-95 p-4"
        )}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
      >
        {isRecording ? (
          <>
            <Square className="h-5 w-5 fill-current" />
            <span className="text-sm font-medium tabular-nums">
              {formatDuration(elapsedSeconds * 1000)}
            </span>
          </>
        ) : (
          <Mic className="h-5 w-5" />
        )}
      </button>

      <RecordingPrepareSheet
        payload={pendingPayload}
        onClose={() => setPendingPayload(null)}
      />
    </>
  )
}
