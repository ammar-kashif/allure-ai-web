"use client"

import { useEffect } from "react"
import { Mic, Square } from "lucide-react"
import { toast } from "sonner"

import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { useUploadRecording } from "@/hooks/use-recordings"
import { useRecordingStore } from "@/stores/recording-store"
import { PostRecordingDialog } from "@/components/recording/post-recording-dialog"
import { cn, formatDuration } from "@/lib/utils"

export function RecordingFAB() {
  const { isRecording, elapsedSeconds, startRecording, stopRecording, onRecordingCompleteRef } =
    useAudioRecorder()
  const uploadRecording = useUploadRecording()

  // Wire up the recording complete callback: upload immediately, then open dialog
  useEffect(() => {
    onRecordingCompleteRef.current = (result) => {
      // 1. Start upload immediately in background
      const formData = new FormData()
      formData.append("file", result.blob, `${result.recordingId}.webm`)
      formData.append("recordingId", result.recordingId)
      formData.append("title", result.title)
      formData.append("durationMs", String(result.durationMs))

      uploadRecording.mutate(formData, {
        onError: () => {
          toast.error("Failed to save recording", {
            description: "The recording could not be saved. Please try again.",
          })
        },
      })

      // 2. Open post-recording dialog for metadata entry
      useRecordingStore.getState().openPostRecordingDialog({
        recordingId: result.recordingId,
        defaultTitle: result.title,
        durationMs: result.durationMs,
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

      <PostRecordingDialog />
    </>
  )
}
