"use client"

import { GhostCitationPill } from "./ghost-citation"
import type { GhostMessage } from "./types"

export function GhostMessageRow({ message }: { message: GhostMessage }) {
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[80%] rounded-lg bg-primary/10 px-4 py-3 text-sm">
        {message.content}
      </div>
    )
  }
  return (
    <div className="max-w-[90%] space-y-2">
      <div className="whitespace-pre-wrap text-sm leading-relaxed">
        {message.content}
      </div>
      {message.citations && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {message.citations.map((c, i) => (
            <GhostCitationPill key={i} cite={c} />
          ))}
        </div>
      )}
      {(message.cost_usd != null || message.latency_ms != null) && (
        <div className="pt-1 text-xs text-muted-foreground">
          {message.latency_ms != null && (
            <span>{(message.latency_ms / 1000).toFixed(1)}s</span>
          )}
          {message.latency_ms != null && message.cost_usd != null && (
            <span className="mx-1">·</span>
          )}
          {message.cost_usd != null && (
            <span>${message.cost_usd.toFixed(4)}</span>
          )}
        </div>
      )}
    </div>
  )
}
