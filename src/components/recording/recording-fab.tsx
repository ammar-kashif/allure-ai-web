"use client"

import { useEffect } from "react"
import { Mic, Square } from "lucide-react"
import { toast } from "sonner"

import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { useUploadRecording } from "@/hooks/use-recordings"
import { formatDuration } from "@/lib/utils"
import { cn } from "@/lib/utils"

export function RecordingFAB() {
  const { isRecording, elapsedSeconds, startRecording, stopRecording, onRecordingCompleteRef } =
    useAudioRecorder()
  const uploadRecording = useUploadRecording()

  // Wire up the recording complete callback to save to DB
  useEffect(() => {
    onRecordingCompleteRef.current = (result) => {
      const formData = new FormData()
      formData.append("file", result.blob, `${result.recordingId}.webm`)
      formData.append("recordingId", result.recordingId)
      formData.append("title", result.title)
      formData.append("durationMs", String(result.durationMs))

      uploadRecording.mutate(formData, {
        onSuccess: () => {
          toast.success("Recording saved", {
            description: `"${result.title}" is ready for project assignment.`,
          })
        },
        onError: () => {
          toast.error("Failed to save recording", {
            description: "The recording could not be saved. Please try again.",
          })
        },
      })
    }

    return () => {
      onRecordingCompleteRef.current = null
    }
  }, [onRecordingCompleteRef, uploadRecording])

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
