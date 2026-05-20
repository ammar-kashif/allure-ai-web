"use client"

import { useState } from "react"

import { GhostChat } from "@/components/ghost/ghost-chat"
import { GhostConversationList } from "@/components/ghost/ghost-conversation-list"
import { GhostCostBadge } from "@/components/ghost/ghost-cost-badge"

export default function GhostPage() {
  const [convId, setConvId] = useState<string | undefined>(undefined)
  const [resetKey, setResetKey] = useState(0)

  function newConversation() {
    setConvId(undefined)
    setResetKey((k) => k + 1)
  }

  return (
    <div className="flex h-[calc(100svh-7rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight">Ghost</h1>
          <p className="text-sm text-muted-foreground">
            Project memory across meetings, documents, and tasks.
          </p>
        </div>
        <GhostCostBadge />
      </div>
      <div className="grid flex-1 grid-cols-[260px_1fr] gap-4 overflow-hidden">
        <aside className="overflow-hidden rounded-md border border-border/60 p-2">
          <GhostConversationList
            activeId={convId}
            onSelect={setConvId}
            onNew={newConversation}
          />
        </aside>
        <section className="overflow-hidden rounded-md border border-border/60 px-3">
          <GhostChat key={`${convId ?? "new"}-${resetKey}`} convId={convId} />
        </section>
      </div>
    </div>
  )
}
