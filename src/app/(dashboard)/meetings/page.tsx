"use client"

import { useMemo, useState } from "react"
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  Square,
} from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useLogs } from "@/hooks/use-logs"
import { useStopBotMeeting } from "@/hooks/use-bot-meeting"
import { cn } from "@/lib/utils"
import type { LogEvent, LogStatus } from "@/types/log"

const CATEGORIES = [
  "upload",
  "pipeline",
  "transcription",
  "diarization",
  "extraction",
  "document",
  "bot",
]

const ACTIVE_BOT_EVENTS = new Set([
  "bot.waiting",
  "bot.dispatched",
  "bot.joined",
  "bot.recording_detected",
])

const STATUS_META: Record<
  LogStatus,
  { label: string; icon: typeof Clock; className: string }
> = {
  start: {
    label: "Running",
    icon: Clock,
    className: "border-border text-muted-foreground",
  },
  done: {
    label: "Done",
    icon: CheckCircle2,
    className: "border-border text-foreground",
  },
  failed: {
    label: "Failed",
    icon: AlertCircle,
    className: "border-destructive/40 bg-destructive/10 text-destructive",
  },
}

function fmtTs(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function fmtDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "-"
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`
}

function eventLabel(event: string): string {
  return event
    .split(".")
    .map((part) => part.replace(/_/g, " "))
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function relatedId(log: LogEvent): string {
  return log.dispatch_id || log.job_id || log.recording_id || "-"
}

function StatusBadge({ status }: { status: LogStatus }) {
  const meta = STATUS_META[status]
  const Icon = meta.icon
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-full border px-2 text-xs font-medium",
        meta.className
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {meta.label}
    </span>
  )
}

function CategoryBadge({ category }: { category: string }) {
  const Icon = category === "bot" ? Bot : category === "document" ? FileText : Clock
  return (
    <Badge variant="outline" className="capitalize">
      <Icon className="h-3 w-3" />
      {category}
    </Badge>
  )
}

export default function LogsPage() {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("all")
  const [status, setStatus] = useState("all")
  const filters = {
    limit: 300,
    ...(category !== "all" ? { category } : {}),
    ...(status !== "all" ? { status } : {}),
  }
  const { data = [], isLoading, error, refetch, isFetching } = useLogs(filters)
  const stopBot = useStopBotMeeting()

  const latestBotByDispatch = useMemo(() => {
    const latest = new Map<string, LogEvent>()
    for (const log of data) {
      if (log.category === "bot" && log.dispatch_id && !latest.has(log.dispatch_id)) {
        latest.set(log.dispatch_id, log)
      }
    }
    return latest
  }, [data])

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return data
    return data.filter((log) =>
      [
        log.category,
        log.event,
        log.status,
        log.message,
        log.recording_id,
        log.job_id,
        log.dispatch_id,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle))
    )
  }, [data, query])

  const handleStopBot = (dispatchId: string) => {
    stopBot.mutate(dispatchId, {
      onSuccess: () => {
        toast.success("Stop requested", {
          description: "The bot will leave the meeting and finalize the recording.",
        })
        refetch()
      },
      onError: (err) => {
        toast.error("Could not stop the bot", {
          description: err.message,
        })
      },
    })
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-heading text-2xl font-semibold">Logs</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Operational events from uploads, transcription, diarization,
          extraction, document generation, and meeting bots.
        </p>
      </header>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative max-w-xl flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search logs"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select value={category} onValueChange={(value) => setCategory(value ?? "all")}>
            <SelectTrigger className="w-[160px]">
              <SelectValue>
                {category === "all" ? "All categories" : eventLabel(category)}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {CATEGORIES.map((item) => (
                <SelectItem key={item} value={item}>
                  {eventLabel(item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={status} onValueChange={(value) => setStatus(value ?? "all")}>
            <SelectTrigger className="w-[140px]">
              <SelectValue>
                {status === "all" ? "All statuses" : STATUS_META[status as LogStatus].label}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="start">Running</SelectItem>
              <SelectItem value="done">Done</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-lg border border-border/60 p-8 text-center text-sm text-muted-foreground">
          <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />
          Loading logs...
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive/60 bg-destructive/10 p-4 text-sm text-destructive">
          Could not load logs. Is the backend running?
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-border/60 p-8 text-center text-sm text-muted-foreground">
          No matching log events yet. Start a recording, dispatch a bot, or
          generate a document to populate this feed.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border/60">
          <table className="w-full min-w-[980px] text-sm">
            <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Category</th>
                <th className="px-3 py-2 font-medium">Event</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Message</th>
                <th className="px-3 py-2 font-medium">Duration</th>
                <th className="px-3 py-2 font-medium">Related id</th>
                <th className="px-3 py-2 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((log) => {
                const latestBot = log.dispatch_id
                  ? latestBotByDispatch.get(log.dispatch_id)
                  : null
                const canStopBot =
                  log.category === "bot" &&
                  log.dispatch_id &&
                  latestBot?.id === log.id &&
                  ACTIVE_BOT_EVENTS.has(log.event)

                return (
                  <tr
                    key={log.id}
                    className="border-b border-border/40 hover:bg-muted/30"
                  >
                    <td className="px-3 py-2 align-top text-xs text-muted-foreground whitespace-nowrap">
                      {fmtTs(log.created_at)}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <CategoryBadge category={log.category} />
                    </td>
                    <td className="px-3 py-2 align-top font-medium">
                      {eventLabel(log.event)}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <StatusBadge status={log.status} />
                    </td>
                    <td className="max-w-[28rem] px-3 py-2 align-top text-muted-foreground">
                      {log.message || "-"}
                    </td>
                    <td className="px-3 py-2 align-top font-numeric text-xs text-muted-foreground whitespace-nowrap">
                      {fmtDuration(log.duration_ms)}
                    </td>
                    <td className="max-w-[14rem] truncate px-3 py-2 align-top font-mono text-xs text-muted-foreground">
                      {relatedId(log)}
                    </td>
                    <td className="px-3 py-2 align-top text-right">
                      {canStopBot ? (
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={stopBot.isPending}
                          onClick={() => handleStopBot(log.dispatch_id!)}
                        >
                          {stopBot.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Square className="h-4 w-4 fill-current" />
                          )}
                          Stop
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
