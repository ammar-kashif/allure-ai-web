"use client"

import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { apiClient } from "@/lib/api/client"
import type { GhostSettings } from "./types"

const PROVIDER_MODELS: Record<string, string[]> = {
  anthropic: ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"],
  custom: [],
}

export function GhostSettingsForm() {
  const queryClient = useQueryClient()
  const { data: settings, isLoading } = useQuery({
    queryKey: ["ghost-settings"],
    queryFn: () => apiClient.get<GhostSettings>("/api/ghost/settings"),
  })

  const [provider, setProvider] = useState<"anthropic" | "openai" | "custom">("anthropic")
  const [model, setModel] = useState("claude-opus-4-7")
  const [apiKey, setApiKey] = useState("")
  const [monthlyCap, setMonthlyCap] = useState<number>(50)
  const [baseUrl, setBaseUrl] = useState("")

  useEffect(() => {
    if (!settings) return
    setProvider(settings.provider)
    setModel(settings.model)
    setMonthlyCap(settings.monthly_cap_usd ?? 50)
    setBaseUrl(settings.base_url ?? "")
  }, [settings])

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiClient.patch<GhostSettings>("/api/ghost/settings", payload),
    onSuccess: () => {
      toast.success("Ghost settings updated")
      setApiKey("")
      queryClient.invalidateQueries({ queryKey: ["ghost-settings"] })
      queryClient.invalidateQueries({ queryKey: ["ghost-cost"] })
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Failed to save")
    },
  })

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Mode</CardTitle>
          <CardDescription>
            Ghost answers cross-project questions over your meetings, documents,
            and tasks. Local mode is in development.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={true}
                readOnly
                className="accent-primary"
              />
              <span className="text-sm">Hosted</span>
            </label>
            <label className="flex items-center gap-2 opacity-50">
              <input type="radio" disabled />
              <span className="text-sm">
                Local <span className="text-xs">(coming soon)</span>
              </span>
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Provider</CardTitle>
          <CardDescription>
            Bring your own API key. Stored encrypted at rest when{" "}
            <code className="text-xs">GHOST_SECRET</code> is set on the
            backend.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="provider">Provider</Label>
            <Select
              value={provider}
              onValueChange={(v) => {
                if (!v) return
                const next = v as typeof provider
                setProvider(next)
                const list = PROVIDER_MODELS[next] || []
                if (list.length > 0) setModel(list[0])
              }}
            >
              <SelectTrigger id="provider" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="anthropic">Anthropic</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="custom">Custom (OpenAI-compatible)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="model">Model</Label>
            {provider === "custom" ? (
              <Input
                id="model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. gpt-4o or your-model-id"
              />
            ) : (
              <Select value={model} onValueChange={(v) => v && setModel(v)}>
                <SelectTrigger id="model" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(PROVIDER_MODELS[provider] || []).map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {provider === "custom" && (
            <div>
              <Label htmlFor="base_url">Base URL</Label>
              <Input
                id="base_url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://your-host/v1"
              />
            </div>
          )}

          <div>
            <Label htmlFor="api_key">
              API key{" "}
              {settings?.api_key_set && (
                <span className="text-xs text-muted-foreground">
                  (already set — leave blank to keep)
                </span>
              )}
            </Label>
            <Input
              id="api_key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={settings?.api_key_set ? "••••••••" : "sk-…"}
            />
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
              Ghost stops answering when the month-to-date spend hits this.
              Set to 0 to disable.
            </p>
          </div>

          <Button
            onClick={() =>
              save.mutate({
                provider,
                model,
                monthly_cap_usd: monthlyCap,
                base_url: provider === "custom" ? baseUrl : null,
                ...(apiKey ? { api_key: apiKey } : {}),
              })
            }
            disabled={save.isPending}
          >
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
