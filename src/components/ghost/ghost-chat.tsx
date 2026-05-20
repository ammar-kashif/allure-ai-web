"use client"

import { useEffect, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Send } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { apiClient } from "@/lib/api/client"
import { GhostMessageRow } from "./ghost-message"
import type { GhostAskResponse, GhostConversation, GhostMessage } from "./types"

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export function GhostChat({ convId: initialConvId }: { convId?: string }) {
  const queryClient = useQueryClient()
  const [convId, setConvId] = useState<string | undefined>(initialConvId)
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  // Optimistic message list; replaced by server data after a refetch.
  const [optimistic, setOptimistic] = useState<GhostMessage[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: conv } = useQuery({
    queryKey: ["ghost-conversation", convId],
    queryFn: async () =>
      convId
        ? apiClient.get<GhostConversation>(`/api/ghost/conversations/${convId}`)
        : undefined,
    enabled: !!convId,
  })

  const messages: GhostMessage[] = conv?.messages ?? optimistic

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  async function send() {
    const question = draft.trim()
    if (!question || busy) return
    setBusy(true)
    setOptimistic((m) => [
      ...m,
      {
        id: generateId(),
        conv_id: convId ?? "pending",
        role: "user",
        content: question,
        created_at: new Date().toISOString(),
      },
    ])
    setDraft("")
    try {
      const res = await apiClient.post<GhostAskResponse>("/api/ghost/ask", {
        question,
        conv_id: convId,
      })
      setConvId(res.conv_id)
      // Refetch the conversation to pull canonical message rows.
      queryClient.invalidateQueries({ queryKey: ["ghost-conversation", res.conv_id] })
      queryClient.invalidateQueries({ queryKey: ["ghost-conversations"] })
      queryClient.invalidateQueries({ queryKey: ["ghost-cost"] })
      setOptimistic([])
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ghost failed"
      toast.error(message)
      // Surface a synthetic assistant error message in the thread.
      setOptimistic((m) => [
        ...m,
        {
          id: generateId(),
          conv_id: convId ?? "pending",
          role: "assistant",
          content: `(error) ${message}`,
          created_at: new Date().toISOString(),
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-1 py-4 space-y-4">
        {messages.length === 0 && (
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
        {messages.map((m) => (
          <GhostMessageRow key={m.id} message={m} />
        ))}
        {busy && (
          <div className="text-xs text-muted-foreground px-2">
            Thinking…
          </div>
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
          />
          <Button onClick={() => void send()} disabled={busy || !draft.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
