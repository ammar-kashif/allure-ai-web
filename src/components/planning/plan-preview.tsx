"use client"

import { useState, useCallback } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Wand2, CheckCircle2, XCircle, CheckCheck, X, ChevronDown, ChevronRight,
  AlertTriangle, ListTodo, Milestone, Loader2, RefreshCw
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { apiClient } from "@/lib/api/client"
import { addDays, format } from "date-fns"

interface PlanTask {
  title: string
  detail: string
  priority: "high" | "medium" | "low"
  milestone: string | null
  dueOffset: number | null
}

interface PlanMilestone {
  title: string
  startOffset: number
  endOffset: number
}

interface PlanRisk {
  title: string
  detail: string
}

interface Plan {
  tasks: PlanTask[]
  milestones: PlanMilestone[]
  risks: PlanRisk[]
}

interface AcceptState {
  tasks: boolean[]
  milestones: boolean[]
}

interface PlanPreviewProps {
  recordingId: string
  projectId?: string
}

const priorityColors = {
  high: "text-red-600 bg-red-50 border-red-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200",
  low: "text-muted-foreground bg-muted border-border",
}

export function PlanPreview({ recordingId, projectId }: PlanPreviewProps) {
  const queryClient = useQueryClient()
  const [plan, setPlan] = useState<Plan | null>(null)
  const [accept, setAccept] = useState<AcceptState>({ tasks: [], milestones: [] })
  const [projectGoal, setProjectGoal] = useState("")
  const [expandedRisks, setExpandedRisks] = useState(false)

  const generateMutation = useMutation({
    mutationFn: () =>
      apiClient.post<Plan>(`/api/recordings/${recordingId}/generate-plan`, {
        projectGoal: projectGoal.trim() || undefined,
      }),
    onSuccess: (data) => {
      setPlan(data)
      setAccept({
        tasks: data.tasks.map(() => true),
        milestones: data.milestones.map(() => true),
      })
    },
    onError: () => toast.error("Plan generation failed"),
  })

  const acceptMutation = useMutation({
    mutationFn: async () => {
      if (!plan || !projectId) return

      const today = new Date()

      // Create accepted milestones first
      const milestoneMap = new Map<string, string>() // title -> created id
      for (let i = 0; i < plan.milestones.length; i++) {
        if (!accept.milestones[i]) continue
        const m = plan.milestones[i]
        const created = await apiClient.post<{ id: string }>("/api/milestones", {
          projectId,
          title: m.title,
          startDate: format(addDays(today, m.startOffset), "yyyy-MM-dd"),
          endDate: format(addDays(today, m.endOffset), "yyyy-MM-dd"),
        })
        milestoneMap.set(m.title, created.id)
      }

      // Create accepted tasks
      for (let i = 0; i < plan.tasks.length; i++) {
        if (!accept.tasks[i]) continue
        const t = plan.tasks[i]
        await apiClient.post("/api/tasks", {
          title: t.title,
          detail: t.detail,
          priority: t.priority,
          dueDate: t.dueOffset != null ? format(addDays(today, t.dueOffset), "yyyy-MM-dd") : null,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["milestones"] })
      toast.success("Plan accepted — tasks and milestones created")
      setPlan(null)
    },
    onError: () => toast.error("Failed to accept plan"),
  })

  function toggleTask(i: number) {
    setAccept((prev) => {
      const tasks = [...prev.tasks]
      tasks[i] = !tasks[i]
      return { ...prev, tasks }
    })
  }

  function toggleMilestone(i: number) {
    setAccept((prev) => {
      const milestones = [...prev.milestones]
      milestones[i] = !milestones[i]
      return { ...prev, milestones }
    })
  }

  const acceptAllTasks = useCallback(() => {
    setAccept((prev) => ({ ...prev, tasks: prev.tasks.map(() => true) }))
  }, [])
  const rejectAllTasks = useCallback(() => {
    setAccept((prev) => ({ ...prev, tasks: prev.tasks.map(() => false) }))
  }, [])

  const acceptedTaskCount = accept.tasks.filter(Boolean).length
  const acceptedMilestoneCount = accept.milestones.filter(Boolean).length

  if (!plan) {
    return (
      <div className="space-y-4 rounded-xl border bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-primary" />
          <h3 className="font-heading font-semibold">AI Project Plan</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Generate a project plan from this meeting&apos;s outcomes and transcript. The AI will propose tasks, milestones, and risks you can preview and selectively accept.
        </p>
        <div className="space-y-1.5">
          <Label className="text-xs">Project goal (optional)</Label>
          <Input
            placeholder="e.g. Launch MVP by Q3 2026"
            value={projectGoal}
            onChange={(e) => setProjectGoal(e.target.value)}
          />
        </div>
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="gap-2"
        >
          {generateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          {generateMutation.isPending ? "Generating plan…" : "Generate Plan"}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-primary" />
          <h3 className="font-heading font-semibold">AI-Generated Plan</h3>
          <span className="text-xs text-muted-foreground">
            {acceptedTaskCount} task{acceptedTaskCount !== 1 ? "s" : ""}, {acceptedMilestoneCount} milestone{acceptedMilestoneCount !== 1 ? "s" : ""} selected
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Regenerate
          </Button>
          <Button
            size="sm"
            onClick={() => acceptMutation.mutate()}
            disabled={acceptMutation.isPending || (acceptedTaskCount === 0 && acceptedMilestoneCount === 0)}
            className="gap-1.5"
          >
            {acceptMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCheck className="h-3.5 w-3.5" />}
            Accept selected
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setPlan(null)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Milestones */}
      {plan.milestones.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-sm font-semibold">
            <Milestone className="h-4 w-4 text-muted-foreground" />
            Milestones ({plan.milestones.length})
          </div>
          <div className="space-y-1.5">
            {plan.milestones.map((m, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
                  accept.milestones[i] ? "border-primary/30 bg-primary/5" : "opacity-50"
                )}
              >
                <button onClick={() => toggleMilestone(i)} className="shrink-0">
                  {accept.milestones[i] ? (
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                  ) : (
                    <XCircle className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-sm">{m.title}</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    Days {m.startOffset}–{m.endOffset}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-sm font-semibold">
            <ListTodo className="h-4 w-4 text-muted-foreground" />
            Tasks ({plan.tasks.length})
          </div>
          <div className="flex items-center gap-1.5">
            <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={acceptAllTasks}>
              <CheckCheck className="h-3 w-3" /> All
            </Button>
            <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={rejectAllTasks}>
              <X className="h-3 w-3" /> None
            </Button>
          </div>
        </div>

        <div className="space-y-1.5">
          {plan.tasks.map((t, i) => (
            <div
              key={i}
              className={cn(
                "rounded-lg border px-3 py-2.5 transition-colors",
                accept.tasks[i] ? "border-primary/30 bg-primary/5" : "opacity-50"
              )}
            >
              <div className="flex items-start gap-3">
                <button onClick={() => toggleTask(i)} className="shrink-0 mt-0.5">
                  {accept.tasks[i] ? (
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                  ) : (
                    <XCircle className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{t.title}</span>
                    <span className={cn("rounded-full border px-1.5 py-0.5 text-[10px] font-medium capitalize", priorityColors[t.priority])}>
                      {t.priority}
                    </span>
                    {t.milestone && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        {t.milestone}
                      </span>
                    )}
                    {t.dueOffset != null && (
                      <span className="text-[10px] text-muted-foreground">Day {t.dueOffset}</span>
                    )}
                  </div>
                  {t.detail && (
                    <p className="text-xs text-muted-foreground">{t.detail}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Risks */}
      {plan.risks.length > 0 && (
        <div className="space-y-2">
          <button
            className="flex items-center gap-1.5 text-sm font-semibold w-full"
            onClick={() => setExpandedRisks((v) => !v)}
          >
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Identified risks ({plan.risks.length})
            {expandedRisks ? <ChevronDown className="h-3.5 w-3.5 ml-auto" /> : <ChevronRight className="h-3.5 w-3.5 ml-auto" />}
          </button>

          {expandedRisks && (
            <div className="space-y-2">
              {plan.risks.map((r, i) => (
                <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 space-y-1">
                  <p className="text-sm font-medium text-amber-800">{r.title}</p>
                  <p className="text-xs text-amber-700">{r.detail}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
