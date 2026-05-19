"use client"

import { useEffect, useState } from "react"
import { Bot, Mic, Square } from "lucide-react"
import { toast } from "sonner"

import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { useUploadRecording } from "@/hooks/use-recordings"
import { useRecordingStore } from "@/stores/recording-store"
import { BotDispatchDialog } from "@/components/recording/bot-dispatch-dialog"
import { PostRecordingDialog } from "@/components/recording/post-recording-dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn, formatDuration } from "@/lib/utils"

export function RecordingFAB() {
  const { isRecording, elapsedSeconds, startRecording, stopRecording, onRecordingCompleteRef } =
    useAudioRecorder()
  const uploadRecording = useUploadRecording()

  const [botDialogOpen, setBotDialogOpen] = useState(false)

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

  // While natively recording, the button is the stop control; no menu.
  if (isRecording) {
    return (
      <>
        <button
          onClick={() => stopRecording()}
          className={cn(
            "fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full transition-[transform,box-shadow,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]",
            "focus:outline-none focus-visible:shadow-[var(--shadow-focus)]",
            "bg-destructive px-4 py-2.5 text-background shadow-[var(--shadow-md)] hover:shadow-[var(--shadow-lg)] active:scale-[0.97]"
          )}
          aria-label="Stop recording"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-background opacity-70" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-background" />
          </span>
          <span className="text-sm font-medium font-numeric">
            {formatDuration(elapsedSeconds * 1000)}
          </span>
          <Square className="h-3.5 w-3.5 fill-current" />
        </button>
        <PostRecordingDialog />
      </>
    )
  }

  // Idle: clicking the mic opens a menu with two ways to start recording.
  // (DropdownMenuTrigger renders as its own <button> via @base-ui/react, so
  // we pass classes/children directly rather than nesting a child <button>.)
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Start recording"
          className={cn(
            "fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full transition-[transform,box-shadow,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]",
            "focus:outline-none focus-visible:shadow-[var(--shadow-focus)]",
            "bg-foreground p-4 text-background shadow-[var(--shadow-md)] hover:shadow-[var(--shadow-lg)] hover:-translate-y-0.5 active:scale-[0.97]"
          )}
        >
          <Mic className="h-5 w-5" strokeWidth={1.75} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="top" className="w-64">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Start a recording</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => startRecording()}>
              <Mic className="mr-2 h-4 w-4" strokeWidth={1.75} />
              <div className="flex flex-col">
                <span>Record this device</span>
                <span className="text-xs text-muted-foreground">
                  Mic + system audio via the browser
                </span>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setBotDialogOpen(true)}>
              <Bot className="mr-2 h-4 w-4" strokeWidth={1.75} />
              <div className="flex flex-col">
                <span>Send bot to a meeting</span>
                <span className="text-xs text-muted-foreground">
                  Paste a Meet / Teams / Zoom link
                </span>
              </div>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      <BotDispatchDialog
        open={botDialogOpen}
        onOpenChange={setBotDialogOpen}
      />
      <PostRecordingDialog />
    </>
  )
}
