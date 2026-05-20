"use client"

import { useState } from "react"
import { AlertTriangle, ChevronDown, ChevronRight, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAutonomyRun, useUndoAutonomyAction, useUndoAutonomyRun } from "@/hooks/use-autonomy"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"

import type { AutonomyAction } from "./types"

const KIND_LABELS: Record<string, string> = {
  task_created: "New task",
  task_discussed: "Discussed",
  task_appears_done: "Appears done",
  task_appears_blocked: "Appears blocked",
  skipped_duplicate: "Skipped (duplicate)",
  skipped_verifier: "Skipped (verifier)",
  skipped_gate: "Skipped (gate)",
}

function formatTimestampFromIndex(_idx: number | null): string {
  // The action carries segment_index but not directly timestamp; the
  // banner uses setHighlight(idx) which is enough to jump. Kept here as
  // a placeholder for future timestamp display.
  return ""
}

function ActionRow({
  action,
  recordingId,
  onUndo,
  undoing,
}: {
  action: AutonomyAction
  recordingId: string
  onUndo: (id: string) => void
  undoing: boolean
}) {
  const setHighlight = useEvidenceHighlight((s) => s.setHighlight)
  const payload = action.detector_payload as Record<string, unknown> | undefined
  const title = (payload?.title as string) || (payload?.reason as string) || action.reason
  const owner = (payload?.owner_name as string) || ""

  const isReversed = !!action.reversed_at
  const isCreated = action.kind === "task_created"
  const isSkipped = action.kind.startsWith("skipped_")

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 ${
        isReversed
          ? "border-border/50 bg-muted/30 opacity-60"
          : isSkipped
            ? "border-border/60 bg-background/40"
            : "border-destructive/30 bg-background"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={isSkipped ? "outline" : "secondary"} className="shrink-0">
            {KIND_LABELS[action.kind] ?? action.kind}
          </Badge>
          <span className="truncate text-sm font-medium">{title || "(no title)"}</span>
          {owner && <span className="text-xs text-muted-foreground">· {owner}</span>}
          {action.segment_index !== null && (
            <button
              type="button"
              onClick={() => setHighlight(action.segment_index!)}
              className="text-xs text-primary hover:underline"
            >
              jump to segment #{action.segment_index}
              {formatTimestampFromIndex(action.segment_index)}
            </button>
          )}
        </div>
        {action.reason && (
          <div className="mt-1 text-xs text-muted-foreground">{action.reason}</div>
        )}
        {action.verifier_reason && (
          <div className="mt-0.5 text-xs italic text-muted-foreground">
            verifier: {action.verifier_reason}
          </div>
        )}
      </div>
      {isCreated && !isReversed && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onUndo(action.id)}
          disabled={undoing}
        >
          {undoing ? <Loader2 className="h-3 w-3 animate-spin" /> : "Undo"}
        </Button>
      )}
      {isReversed && (
        <span className="text-xs text-muted-foreground shrink-0">reversed</span>
      )}
    </div>
  )
}

export function AutonomyBanner({ recordingId }: { recordingId: string }) {
  const { data, isLoading } = useAutonomyRun(recordingId)
  const undoAction = useUndoAutonomyAction(recordingId)
  const undoRun = useUndoAutonomyRun(recordingId)
  const [showSkipped, setShowSkipped] = useState(false)

  if (isLoading || !data || !data.run) return null
  const { run, actions } = data
  if (run.status === "skipped") return null
  const visible = actions.filter(
    (a) => a.kind === "task_created" || a.kind.startsWith("task_"),
  )
  const skipped = actions.filter((a) => a.kind.startsWith("skipped_"))
  const totalSurfaced = visible.length
  if (totalSurfaced === 0) return null

  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 my-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 text-destructive" />
          <div>
            <div className="text-sm font-semibold text-destructive">
              Autonomy found follow-ups
            </div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {run.tasks_created} new task{run.tasks_created === 1 ? "" : "s"} created · {" "}
              {run.tasks_discussed} prior task{run.tasks_discussed === 1 ? "" : "s"} discussed
              {skipped.length > 0 && (
                <span> · {skipped.length} skipped</span>
              )}
              {run.follow_up_to.length > 0 && (
                <span> · follow-up to {run.follow_up_to.length} prior meeting{run.follow_up_to.length === 1 ? "" : "s"}</span>
              )}
              {typeof run.cost_usd === "number" && (
                <span> · ${run.cost_usd.toFixed(4)}</span>
              )}
            </div>
          </div>
        </div>
        {run.tasks_created > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => undoRun.mutate(run.id)}
            disabled={undoRun.isPending}
          >
            {undoRun.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Undo all"}
          </Button>
        )}
      </div>

      <div className="mt-3 space-y-1.5">
        {visible.map((a) => (
          <ActionRow
            key={a.id}
            action={a}
            recordingId={recordingId}
            onUndo={(id) => undoAction.mutate(id)}
            undoing={undoAction.isPending && undoAction.variables === a.id}
          />
        ))}
      </div>

      {skipped.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowSkipped((s) => !s)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            {showSkipped ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            {skipped.length} skipped action{skipped.length === 1 ? "" : "s"}
          </button>
          {showSkipped && (
            <div className="mt-2 space-y-1.5">
              {skipped.map((a) => (
                <ActionRow
                  key={a.id}
                  action={a}
                  recordingId={recordingId}
                  onUndo={() => undefined}
                  undoing={false}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
