"use client"

import { GhostSettingsForm } from "@/components/ghost/ghost-settings-form"

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Ghost provider, API key, and monthly spending cap.
        </p>
      </div>
      <GhostSettingsForm />
    </div>
  )
}
