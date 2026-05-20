"use client"

import { ChevronDown, ChevronRight, Loader2 } from "lucide-react"
import { useState } from "react"

import type { GhostStreamEvent } from "./types"

function describeArgs(args?: Record<string, unknown>): string {
  if (!args) return ""
  const bits: string[] = []
  if (typeof args.query === "string" && args.query) bits.push(`"${args.query}"`)
  if (typeof args.name === "string" && args.name) bits.push(`"${args.name}"`)
  if (typeof args.entity_id === "string" && args.entity_id) bits.push(`id=${args.entity_id.slice(0, 8)}`)
  if (typeof args.speaker === "string" && args.speaker) bits.push(`speaker=${args.speaker}`)
  if (typeof args.outcome_type === "string" && args.outcome_type) bits.push(args.outcome_type)
  if (typeof args.kind === "string" && args.kind) bits.push(args.kind)
  if (typeof args.recording_id === "string" && args.recording_id) bits.push(`rec=${args.recording_id.slice(0, 8)}`)
  if (typeof args.recordings === "number") bits.push(`${args.recordings} rec`)
  if (typeof args.projects === "number") bits.push(`${args.projects} proj`)
  return bits.join(" · ")
}

const TOOL_LABELS: Record<string, string> = {
  resolve_entity: "Resolving entity",
  list_recent_activity: "Pulling recent activity",
  search_transcripts: "Searching transcripts",
  search_attachments: "Searching documents",
  search_outcomes: "Searching outcomes",
  get_recording_summary: "Loading recording",
  get_transcript_window: "Expanding transcript window",
  list_recordings: "Listing recordings",
  spawn_research_subagents: "Spawning sub-investigations",
}

function labelFor(name: string): string {
  return TOOL_LABELS[name] ?? name
}

export type ActivityRow =
  | { kind: "triage"; intent: string; scope: string }
  | { kind: "tool"; name: string; arguments?: Record<string, unknown>; status: "running" | "done" | "error"; summary?: string }
  | { kind: "subagent.spawning"; task_count: number; questions: string[] }
  | { kind: "subagent"; question: string; status: "running" | "done" | "error" }
  | { kind: "error"; message: string }

export function eventsToRows(events: GhostStreamEvent[]): ActivityRow[] {
  const rows: ActivityRow[] = []
  for (const ev of events) {
    if (ev.kind === "heartbeat") continue
    if (ev.kind === "triage") {
      rows.push({ kind: "triage", intent: ev.intent, scope: ev.scope })
      continue
    }
    if (ev.kind === "tool.start") {
      rows.push({ kind: "tool", name: ev.name, arguments: ev.arguments, status: "running" })
      continue
    }
    if (ev.kind === "tool.done") {
      // Find the last running tool with this name and flip its status.
      for (let i = rows.length - 1; i >= 0; i--) {
        const r = rows[i]
        if (r.kind === "tool" && r.name === ev.name && r.status === "running") {
          rows[i] = { ...r, status: ev.error ? "error" : "done", summary: ev.summary }
          break
        }
      }
      continue
    }
    if (ev.kind === "subagent.spawning") {
      rows.push({ kind: "subagent.spawning", task_count: ev.task_count, questions: ev.questions })
      continue
    }
    if (ev.kind === "subagent.started") {
      rows.push({ kind: "subagent", question: ev.question, status: "running" })
      continue
    }
    if (ev.kind === "subagent.done") {
      for (let i = rows.length - 1; i >= 0; i--) {
        const r = rows[i]
        if (r.kind === "subagent" && r.question === ev.question && r.status === "running") {
          rows[i] = { ...r, status: ev.error ? "error" : "done" }
          break
        }
      }
      continue
    }
    if (ev.kind === "error") {
      rows.push({ kind: "error", message: ev.message })
      continue
    }
  }
  return rows
}

function RowLine({ row }: { row: ActivityRow }) {
  if (row.kind === "triage") {
    return (
      <div className="text-xs text-muted-foreground">
        Triage · {row.intent} · {row.scope}
      </div>
    )
  }
  if (row.kind === "tool") {
    const args = describeArgs(row.arguments)
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {row.status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <span className={row.status === "error" ? "text-destructive" : ""}>·</span>
        )}
        <span>{labelFor(row.name)}</span>
        {args && <span className="opacity-70">{args}</span>}
        {row.summary && row.status !== "running" && (
          <span className="opacity-60">— {row.summary}</span>
        )}
      </div>
    )
  }
  if (row.kind === "subagent.spawning") {
    return (
      <div className="text-xs text-muted-foreground">
        Spawning {row.task_count} sub-investigation{row.task_count === 1 ? "" : "s"}
      </div>
    )
  }
  if (row.kind === "subagent") {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground pl-3">
        {row.status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <span>·</span>
        )}
        <span className="truncate">{row.question}</span>
      </div>
    )
  }
  if (row.kind === "error") {
    return <div className="text-xs text-destructive">{row.message}</div>
  }
  return null
}

export function GhostActivity({
  rows,
  done = false,
}: {
  rows: ActivityRow[]
  done?: boolean
}) {
  const [collapsed, setCollapsed] = useState(false)
  if (rows.length === 0) return null

  const summary = (() => {
    const tools = rows.filter((r) => r.kind === "tool")
    const completed = tools.filter((r) => r.kind === "tool" && r.status !== "running").length
    if (done) return `${completed} step${completed === 1 ? "" : "s"}`
    const inFlight = tools.find((r) => r.kind === "tool" && r.status === "running")
    if (inFlight && inFlight.kind === "tool") return labelFor(inFlight.name)
    return "Thinking…"
  })()

  return (
    <div className="rounded-md border border-border/60 bg-muted/30 px-3 py-2 my-2">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex w-full items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        {!done && (
          <Loader2 className="h-3 w-3 animate-spin mr-1" />
        )}
        <span className="font-medium">{summary}</span>
      </button>
      {!collapsed && (
        <div className="mt-2 space-y-1">
          {rows.map((r, i) => (
            <RowLine key={i} row={r} />
          ))}
        </div>
      )}
    </div>
  )
}
