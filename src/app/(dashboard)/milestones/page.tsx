"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Milestone, Calendar, CheckCircle2, Circle, Loader2, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { toast } from "sonner"
import type { MilestoneWithProgress } from "@/types/milestone"

export default function MilestonesPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ title: "", detail: "", projectId: "", startDate: "", endDate: "" })

  const { data: milestones = [], isLoading } = useQuery<MilestoneWithProgress[]>({
    queryKey: ["milestones"],
    queryFn: () => apiClient.get("/api/milestones"),
  })

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.get("/api/projects"),
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => apiClient.post("/api/milestones", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones"] })
      setOpen(false)
      setForm({ title: "", detail: "", projectId: "", startDate: "", endDate: "" })
      toast.success("Milestone created")
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.patch(`/api/milestones/${id}`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["milestones"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/milestones/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones"] })
      toast.success("Milestone deleted")
    },
  })

  const statusConfig = {
    upcoming: { label: "Upcoming", icon: Circle, color: "text-muted-foreground" },
    in_progress: { label: "In Progress", icon: Loader2, color: "text-blue-600" },
    completed: { label: "Completed", icon: CheckCircle2, color: "text-green-600" },
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em]">Milestones</h1>
          <p className="mt-1 text-[0.9375rem] text-muted-foreground">
            Track project milestones and roll-up task progress.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-1.5" />
              New Milestone
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Milestone</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-2">
              <div className="space-y-1.5">
                <Label>Title</Label>
                <Input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Milestone title"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Project</Label>
                <Select
                  value={form.projectId}
                  onValueChange={(v) => setForm({ ...form, projectId: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select project" />
                  </SelectTrigger>
                  <SelectContent>
                    {(projects as { id: string; name: string }[]).map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Start date</Label>
                  <Input
                    type="date"
                    value={form.startDate}
                    onChange={(e) => setForm({ ...form, startDate: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>End date</Label>
                  <Input
                    type="date"
                    value={form.endDate}
                    onChange={(e) => setForm({ ...form, endDate: e.target.value })}
                  />
                </div>
              </div>
              <Button
                className="w-full"
                onClick={() => createMutation.mutate(form)}
                disabled={!form.title || !form.projectId || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating…" : "Create"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading milestones…
        </div>
      ) : milestones.length === 0 ? (
        <div className="py-20 text-center">
          <Milestone className="mx-auto h-10 w-10 text-muted-foreground/40 mb-3" />
          <p className="text-muted-foreground">No milestones yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {milestones.map((m) => {
            const cfg = statusConfig[m.status]
            const Icon = cfg.icon
            return (
              <div
                key={m.id}
                className="rounded-xl border bg-card p-5 shadow-[var(--shadow-card)] space-y-3"
              >
                <div className="flex items-start gap-3">
                  <Icon className={cn("h-5 w-5 mt-0.5 shrink-0", cfg.color, m.status === "in_progress" && "animate-spin")} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-heading font-semibold truncate">{m.title}</h3>
                      <div className="flex items-center gap-2 shrink-0">
                        <Select
                          value={m.status}
                          onValueChange={(status) => updateMutation.mutate({ id: m.id, status })}
                        >
                          <SelectTrigger className="h-7 text-xs w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="upcoming">Upcoming</SelectItem>
                            <SelectItem value="in_progress">In Progress</SelectItem>
                            <SelectItem value="completed">Completed</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => deleteMutation.mutate(m.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>

                    {(m.startDate || m.endDate) && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground mt-0.5">
                        <Calendar className="h-3 w-3" />
                        {m.startDate && <span>{m.startDate}</span>}
                        {m.startDate && m.endDate && <span>→</span>}
                        {m.endDate && <span>{m.endDate}</span>}
                      </div>
                    )}
                  </div>
                </div>

                {m.progress && m.progress.total > 0 && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{m.progress.done} / {m.progress.total} tasks done</span>
                      <span>{m.progress.pct}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${m.progress.pct}%` }}
                      />
                    </div>
                  </div>
                )}

                {m.progress?.total === 0 && (
                  <p className="text-xs text-muted-foreground">No tasks linked to this milestone.</p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
