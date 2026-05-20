"use client"

import { useEffect, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Send } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { apiClient } from "@/lib/api/client"
import { eventsToRows, GhostActivity } from "./ghost-activity"
import { GhostMessageRow } from "./ghost-message"
import type {
  GhostConversation,
  GhostMessage,
  GhostStreamEvent,
} from "./types"

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

type TurnState = {
  question: string
  events: GhostStreamEvent[]
  finalMessage: GhostMessage | null
  error?: string
}

export function GhostChat({ convId: initialConvId }: { convId?: string }) {
  const queryClient = useQueryClient()
  const [convId, setConvId] = useState<string | undefined>(initialConvId)
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  const [turn, setTurn] = useState<TurnState | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: conv } = useQuery({
    queryKey: ["ghost-conversation", convId],
    queryFn: async () =>
      convId
        ? apiClient.get<GhostConversation>(`/api/ghost/conversations/${convId}`)
        : undefined,
    enabled: !!convId,
  })

  const persistedMessages: GhostMessage[] = conv?.messages ?? []

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [persistedMessages.length, turn?.events.length])

  async function send() {
    const question = draft.trim()
    if (!question || busy) return
    setBusy(true)
    setDraft("")
    setTurn({ question, events: [], finalMessage: null })

    try {
      const resp = await fetch("/api/ghost/ask-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, conv_id: convId }),
      })
      if (!resp.ok || !resp.body) {
        const text = await resp.text().catch(() => "Ghost failed")
        throw new Error(text)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ""
      let finalEvent: Extract<GhostStreamEvent, { kind: "final" }> | null = null
      let errorEvent: Extract<GhostStreamEvent, { kind: "error" }> | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split("\n\n")
        buf = parts.pop() ?? ""
        for (const block of parts) {
          const dataLine = block.split("\n").find((l) => l.startsWith("data: "))
          if (!dataLine) continue
          const payload = dataLine.slice(6)
          try {
            const ev = JSON.parse(payload) as GhostStreamEvent
            if (ev.kind === "final") finalEvent = ev
            else if (ev.kind === "error") errorEvent = ev
            setTurn((prev) =>
              prev ? { ...prev, events: [...prev.events, ev] } : prev,
            )
          } catch {
            // ignore malformed events
          }
        }
      }

      if (errorEvent) {
        throw new Error(errorEvent.message)
      }
      if (finalEvent) {
        setConvId(finalEvent.conv_id)
        queryClient.invalidateQueries({
          queryKey: ["ghost-conversation", finalEvent.conv_id],
        })
        queryClient.invalidateQueries({ queryKey: ["ghost-conversations"] })
        queryClient.invalidateQueries({ queryKey: ["ghost-cost"] })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ghost failed"
      toast.error(message)
      setTurn((prev) => (prev ? { ...prev, error: message } : prev))
    } finally {
      setBusy(false)
    }
  }

  // Compose the display list: persisted messages followed by the in-flight
  // turn (its user message + activity panel until the final event lands and
  // the conversation refetch absorbs it).
  const showInFlightTurn =
    turn !== null &&
    // If the refetched conversation already includes the latest user turn,
    // drop the optimistic version to avoid duplicates.
    !persistedMessages.some(
      (m) => m.role === "user" && m.content === turn.question,
    )

  const activityRows = turn ? eventsToRows(turn.events) : []

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-1 py-4 space-y-4">
        {persistedMessages.length === 0 && !turn && (
          <div className="text-sm text-muted-foreground px-2">
            <p className="font-medium text-foreground mb-1">Ghost</p>
            <p>
              Ask anything about your meetings, projects, people, or documents.
              Try:
            </p>
            <ul className="mt-2 list-disc pl-4 space-y-1">
              <li>When did we discuss the $400 quotation with John?</li>
              <li>What&apos;s the latest update on Jason?</li>
              <li>Summarize all blockers across projects this month.</li>
            </ul>
          </div>
        )}
        {persistedMessages.map((m) => (
          <GhostMessageRow key={m.id} message={m} />
        ))}
        {showInFlightTurn && (
          <>
            <div className="ml-auto max-w-[80%] rounded-lg bg-primary/10 px-4 py-3 text-sm">
              {turn!.question}
            </div>
            <GhostActivity rows={activityRows} done={!busy} />
          </>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-border/60 pt-3">
        <div className="flex gap-2 items-end">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask Ghost…"
            rows={2}
            className="resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                void send()
              }
            }}
            disabled={busy}
          />
          <Button onClick={() => void send()} disabled={busy || !draft.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
