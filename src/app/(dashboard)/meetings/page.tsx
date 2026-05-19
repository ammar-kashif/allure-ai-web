"use client"

import { AlertCircle, Bot, CheckCircle2, Clock, Loader2, Square } from "lucide-react"
import { toast } from "sonner"

import { useBotMeetings, useStopBotMeeting } from "@/hooks/use-bot-meeting"
import {
  type BotMeetingStatus,
  type BotMeetingState,
} from "@/types/meeting-bot"
import { cn } from "@/lib/utils"

const STATUS_META: Record<
  BotMeetingStatus,
  { label: string; icon: typeof Bot; tone: string }
> = {
  dispatched: { label: "Waiting to join", icon: Clock, tone: "text-muted-foreground" },
  recording: { label: "Recording", icon: Bot, tone: "text-destructive" },
  stop_requested: { label: "Stopping", icon: Loader2, tone: "text-muted-foreground" },
  forwarding: { label: "Uploading", icon: Loader2, tone: "text-muted-foreground" },
  ingested: { label: "Sent to pipeline", icon: CheckCircle2, tone: "text-foreground" },
  failed: { label: "Failed", icon: AlertCircle, tone: "text-destructive" },
}

function StatusPill({ status }: { status: BotMeetingStatus }) {
  const meta = STATUS_META[status]
  const Icon = meta.icon
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border/60 px-2 py-0.5 text-xs",
        meta.tone
      )}
    >
      <Icon
        className={cn(
          "h-3 w-3",
          status === "stop_requested" || status === "forwarding"
            ? "animate-spin"
            : null
        )}
      />
      {meta.label}
    </span>
  )
}

function fmtTs(iso: string | null): string {
  if (!iso) return "—"
  try {
    const d = new Date(iso.replace(" ", "T") + (iso.endsWith("Z") ? "" : "Z"))
    return d.toLocaleString()
  } catch {
    return iso
  }
}

function Row({ row }: { row: BotMeetingState }) {
  const stop = useStopBotMeeting()
  const canStop = row.status === "dispatched" || row.status === "recording"

  return (
    <tr className="border-b border-border/40 hover:bg-muted/30">
      <td className="px-3 py-2 align-top">
        <div className="font-medium">{row.title || "Untitled meeting"}</div>
        <div className="text-xs text-muted-foreground truncate max-w-[28rem]">
          {row.meeting_url}
        </div>
      </td>
      <td className="px-3 py-2 align-top">
        <StatusPill status={row.status} />
      </td>
      <td className="px-3 py-2 align-top text-xs text-muted-foreground whitespace-nowrap">
        {fmtTs(row.dispatched_at)}
      </td>
      <td className="px-3 py-2 align-top text-xs text-muted-foreground whitespace-nowrap">
        {fmtTs(row.finalized_at)}
      </td>
      <td className="px-3 py-2 align-top text-xs text-destructive max-w-[24rem]">
        {row.error ? (
          <span className="line-clamp-3" title={row.error}>
            {row.error}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="px-3 py-2 align-top text-right">
        {canStop ? (
          <button
            type="button"
            disabled={stop.isPending}
            onClick={() =>
              stop.mutate(row.recording_id, {
                onSuccess: () =>
                  toast.success("Stop requested", {
                    description:
                      "The bot will finalize the recording within ~10 seconds.",
                  }),
                onError: (err) =>
                  toast.error("Could not stop the bot", {
                    description: err.message,
                  }),
              })
            }
            className={cn(
              "inline-flex h-7 items-center gap-1 rounded-full px-2.5 text-xs font-medium",
              "bg-destructive text-background hover:shadow-[var(--shadow-sm)] active:scale-[0.97]",
              "focus:outline-none focus-visible:shadow-[var(--shadow-focus)]",
              "disabled:cursor-not-allowed disabled:opacity-60"
            )}
          >
            {stop.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Square className="h-3 w-3 fill-current" />
            )}
            Stop
          </button>
        ) : null}
      </td>
    </tr>
  )
}

export default function MeetingsPage() {
  const { data, isLoading, error } = useBotMeetings()

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="font-heading text-2xl font-semibold">Meetings</h1>
        <p className="text-sm text-muted-foreground">
          Every dispatched bot meeting, with live status from the pipeline.
          Use the Stop button to make the bot leave a meeting it&rsquo;s
          currently recording.
        </p>
      </header>

      {isLoading ? (
        <div className="rounded-lg border border-border/60 p-8 text-center text-sm text-muted-foreground">
          <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />
          Loading meetings…
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive/60 bg-destructive/5 p-4 text-sm text-destructive">
          Could not load meetings. Is the backend running?
        </div>
      ) : !data?.length ? (
        <div className="rounded-lg border border-border/60 p-8 text-center text-sm text-muted-foreground">
          No bot meetings yet. Dispatch one from the floating mic button →
          “Send bot to a meeting”.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border/60">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Meeting</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Dispatched</th>
                <th className="px-3 py-2 font-medium">Finalized</th>
                <th className="px-3 py-2 font-medium">Error</th>
                <th className="px-3 py-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <Row key={row.recording_id} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
