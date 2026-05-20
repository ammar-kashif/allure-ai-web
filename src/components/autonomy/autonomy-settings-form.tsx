"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useProjects } from "@/hooks/use-projects"
import {
  useAutonomyCost,
  useAutonomySettings,
  useUpdateAutonomySettings,
} from "@/hooks/use-autonomy"

export function AutonomySettingsForm() {
  const { data: settings, isLoading } = useAutonomySettings()
  const { data: cost } = useAutonomyCost()
  const { data: projects = [] } = useProjects()
  const update = useUpdateAutonomySettings()

  const [enabled, setEnabled] = useState(true)
  const [monthlyCap, setMonthlyCap] = useState(10)
  const [disabled, setDisabled] = useState<string[]>([])

  useEffect(() => {
    if (!settings) return
    setEnabled(settings.enabled)
    setMonthlyCap(settings.monthly_cap_usd ?? 10)
    setDisabled(settings.disabled_project_ids ?? [])
  }, [settings])

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>
  }

  const toggleProject = (id: string) => {
    setDisabled((d) =>
      d.includes(id) ? d.filter((x) => x !== id) : [...d, id],
    )
  }

  const onSave = () => {
    update.mutate(
      {
        enabled,
        monthly_cap_usd: monthlyCap,
        disabled_project_ids: disabled,
      },
      {
        onSuccess: () => toast.success("Autonomy settings updated"),
        onError: (err: unknown) =>
          toast.error(err instanceof Error ? err.message : "Failed to save"),
      },
    )
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Autonomy</CardTitle>
        <CardDescription>
          Auto-creates follow-up tasks after a meeting is processed, with a
          verifier critic and per-action undo. Disabled projects skip the
          pass entirely.
          {cost && (
            <span className="mt-1 block text-xs">
              This month: ${cost.month_to_date_usd.toFixed(4)} of $
              {cost.monthly_cap_usd.toFixed(2)} cap
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-3">
          <input
            id="autonomy-enabled"
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          <Label htmlFor="autonomy-enabled" className="cursor-pointer">
            Enable autonomous follow-up
          </Label>
        </div>

        <div>
          <Label htmlFor="cap">Monthly cap (USD)</Label>
          <Input
            id="cap"
            type="number"
            min="0"
            step="1"
            value={monthlyCap}
            onChange={(e) => setMonthlyCap(parseFloat(e.target.value) || 0)}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Stops the pass when spend hits this cap. Set to 0 to disable cap.
          </p>
        </div>

        <div>
          <Label>Disabled projects</Label>
          <p className="mb-2 text-xs text-muted-foreground">
            Check a project to skip autonomy for its recordings.
          </p>
          {projects.length === 0 ? (
            <p className="text-xs text-muted-foreground">No projects yet.</p>
          ) : (
            <ul className="space-y-1">
              {projects.map((p) => (
                <li key={p.id} className="flex items-center gap-2 text-sm">
                  <input
                    id={`proj-${p.id}`}
                    type="checkbox"
                    checked={disabled.includes(p.id)}
                    onChange={() => toggleProject(p.id)}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  <Label
                    htmlFor={`proj-${p.id}`}
                    className="cursor-pointer font-normal"
                  >
                    {p.name}
                  </Label>
                </li>
              ))}
            </ul>
          )}
        </div>

        <Button onClick={onSave} disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save"}
        </Button>
      </CardContent>
    </Card>
  )
}
