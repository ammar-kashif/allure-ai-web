"use client"

import { useEffect, useMemo, useState } from "react"
import { Bot, Loader2, Square } from "lucide-react"
import { toast } from "sonner"

import {
  useBotMeetingStatus,
  useStopBotMeeting,
} from "@/hooks/use-bot-meeting"
import { useBotMeetingStore } from "@/stores/bot-meeting-store"
import {
  BOT_ACTIVE_STATES,
  type BotMeetingStatus,
} from "@/types/meeting-bot"
import { cn, formatDuration } from "@/lib/utils"

const STATUS_LABEL: Record<BotMeetingStatus, string> = {
  dispatched: "Waiting to join…",
  recording: "Recording",
  stop_requested: "Stopping…",
  forwarding: "Uploading…",
  ingested: "Sent to pipeline",
  failed: "Failed",
}

/**
 * Floating banner shown whenever there's an active bot meeting session.
 * Sits above the RecordingFAB, polls /api/meetings/{id} every 3s, and
 * disappears once the bot finalizes (ingested/failed).
 */
export function BotRecordingBanner() {
  const recordingId = useBotMeetingStore((s) => s.recordingId)
  const title = useBotMeetingStore((s) => s.title)
  const startedAt = useBotMeetingStore((s) => s.startedAt)
  const clearActive = useBotMeetingStore((s) => s.clear)

  const { data: state } = useBotMeetingStatus(recordingId)
  const stopMutation = useStopBotMeeting()

  // Live elapsed timer
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!startedAt) return
    const interval = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [startedAt])

  // Auto-clear once the bot has finished (or definitively failed)
  useEffect(() => {
    if (!state) return
    if (state.status === "ingested" || state.status === "failed") {
      // Brief delay so the user sees the final state, then clear
      const t = setTimeout(() => clearActive(), 4000)
      return () => clearTimeout(t)
    }
  }, [state, clearActive])

  const elapsedMs = useMemo(
    () => (startedAt ? now - startedAt : 0),
    [now, startedAt]
  )

  if (!recordingId) return null

  const status = state?.status ?? "dispatched"
  const isActive = BOT_ACTIVE_STATES.includes(status)
  const canStop = status === "dispatched" || status === "recording"

  const handleStop = () => {
    if (!recordingId || !canStop || stopMutation.isPending) return
    stopMutation.mutate(recordingId, {
      onSuccess: () =>
        toast.success("Stop requested", {
          description: "The bot will finalize the recording within ~10 seconds.",
        }),
      onError: (err) =>
        toast.error("Could not stop the bot", {
          description: err.message,
        }),
    })
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed bottom-24 right-6 z-50 flex max-w-[22rem] items-center gap-3 rounded-full px-4 py-2.5",
        "border bg-card text-card-foreground shadow-[var(--shadow-md)]",
        status === "failed" ? "border-destructive" : "border-border"
      )}
    >
      <span
        className={cn(
          "relative flex h-2 w-2",
          status === "recording" ? "opacity-100" : "opacity-50"
        )}
        aria-hidden
      >
        {status === "recording" ? (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive opacity-70" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-destructive" />
          </>
        ) : (
          <Bot className="h-3 w-3 text-foreground/60" strokeWidth={1.75} />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {title || "Bot meeting"}
        </p>
        <p className="text-xs text-muted-foreground">
          {STATUS_LABEL[status]}
          {isActive && startedAt ? (
            <span className="ml-1 font-numeric">
              · {formatDuration(elapsedMs)}
            </span>
          ) : null}
        </p>
      </div>

      {canStop ? (
        <button
          type="button"
          onClick={handleStop}
          disabled={stopMutation.isPending}
          aria-label="Stop bot recording"
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-medium",
            "bg-destructive text-background transition-[transform,box-shadow] duration-[var(--duration-fast)]",
            "hover:shadow-[var(--shadow-sm)] active:scale-[0.97]",
            "focus:outline-none focus-visible:shadow-[var(--shadow-focus)]",
            "disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {stopMutation.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Square className="h-3 w-3 fill-current" />
          )}
          Stop
        </button>
      ) : null}
    </div>
  )
}
