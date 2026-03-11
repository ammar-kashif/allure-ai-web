"use client"

import { Mic, Square } from "lucide-react"

import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { formatDuration } from "@/lib/utils"
import { cn } from "@/lib/utils"

export function RecordingFAB() {
  const { isRecording, elapsedSeconds, startRecording, stopRecording } =
    useAudioRecorder()

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <button
      onClick={handleClick}
      className={cn(
        "fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full shadow-lg transition-all duration-200",
        "focus:outline-none focus:ring-2 focus:ring-offset-2",
        isRecording
          ? "animate-pulse bg-red-500 px-4 py-3 text-white hover:bg-red-600 focus:ring-red-500"
          : "bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary p-4"
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
  )
}
