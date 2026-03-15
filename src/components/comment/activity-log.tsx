"use client"

import { useQuery } from "@tanstack/react-query"
import { Clock } from "lucide-react"
import { apiClient } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import { formatDistanceToNow } from "date-fns"
import type { ActivityEntry } from "@/lib/db/activity-log"

interface ActivityLogProps {
  entityType?: string
  entityId?: string
  className?: string
}

const actionColors: Record<string, string> = {
  created: "bg-green-500",
  updated: "bg-blue-500",
  deleted: "bg-red-500",
  promoted: "bg-violet-500",
  approved: "bg-teal-500",
}

export function ActivityLog({ entityType, entityId, className }: ActivityLogProps) {
  const params = new URLSearchParams()
  if (entityType) params.set("entityType", entityType)
  if (entityId) params.set("entityId", entityId)

  const { data: entries = [], isLoading } = useQuery<ActivityEntry[]>({
    queryKey: ["activity", entityType, entityId],
    queryFn: () => apiClient.get(`/api/activity?${params}`),
  })

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading activity…</p>
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No activity recorded yet.</p>

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-1.5 text-sm font-semibold">
        <Clock className="h-4 w-4 text-muted-foreground" />
        Activity
      </div>
      <ol className="relative border-l border-border space-y-4 ml-2">
        {entries.map((entry) => (
          <li key={entry.id} className="ml-4">
            <div
              className={cn(
                "absolute -left-1.5 h-3 w-3 rounded-full border border-background",
                actionColors[entry.action] ?? "bg-muted-foreground"
              )}
            />
            <div className="text-sm">
              <span className="font-medium">{entry.authorName}</span>{" "}
              <span className="text-muted-foreground">{entry.action}</span>{" "}
              <span className="font-medium">{entry.entityType}</span>
              {entry.detail && (
                <span className="text-muted-foreground"> — {entry.detail}</span>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">
              {formatDistanceToNow(new Date(entry.createdAt), { addSuffix: true })}
            </p>
          </li>
        ))}
      </ol>
    </div>
  )
}
