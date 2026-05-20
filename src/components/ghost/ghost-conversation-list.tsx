"use client"

import { useQuery } from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import type { GhostConversation } from "./types"

export function GhostConversationList({
  activeId,
  onSelect,
  onNew,
}: {
  activeId?: string
  onSelect: (id: string) => void
  onNew: () => void
}) {
  const { data: conversations = [] } = useQuery({
    queryKey: ["ghost-conversations"],
    queryFn: () =>
      apiClient.get<GhostConversation[]>("/api/ghost/conversations?limit=50"),
  })

  return (
    <div className="flex h-full flex-col">
      <div className="px-2 pb-2">
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={onNew}
        >
          + New conversation
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 && (
          <p className="px-3 py-2 text-xs text-muted-foreground">
            No conversations yet.
          </p>
        )}
        <ul className="space-y-1 px-1">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onSelect(c.id)}
                className={`w-full truncate rounded px-3 py-2 text-left text-sm transition-colors ${
                  c.id === activeId
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent/60"
                }`}
                title={c.title ?? "(untitled)"}
              >
                {c.title ?? "(untitled)"}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
