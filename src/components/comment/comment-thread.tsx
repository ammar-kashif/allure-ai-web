"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { MessageSquare, Reply, Trash2, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { apiClient } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import { formatDistanceToNow } from "date-fns"
import type { Comment } from "@/lib/db/comments"
import type { CommentEntityType } from "@/lib/db/comments"
import { useAuth } from "@/contexts/auth-context"

interface CommentThreadProps {
  entityType: CommentEntityType
  entityId: string
  className?: string
}

interface CommentItemProps {
  comment: Comment
  entityType: CommentEntityType
  entityId: string
  depth?: number
}

function CommentItem({ comment, entityType, entityId, depth = 0 }: CommentItemProps) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showReply, setShowReply] = useState(false)
  const [replyText, setReplyText] = useState("")

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/comments/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["comments", entityType, entityId] }),
  })

  const replyMutation = useMutation({
    mutationFn: (body: string) =>
      apiClient.post("/api/comments", {
        entityType,
        entityId,
        parentId: comment.id,
        body,
        authorName: user?.name ?? "Anonymous",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments", entityType, entityId] })
      setReplyText("")
      setShowReply(false)
    },
  })

  return (
    <div className={cn("space-y-2", depth > 0 && "ml-6 pl-3 border-l border-border")}>
      <div className="rounded-lg bg-muted/40 px-3 py-2.5 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold">{comment.authorName}</span>
            <span className="text-[10px] text-muted-foreground">
              {formatDistanceToNow(new Date(comment.createdAt), { addSuffix: true })}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {depth === 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setShowReply((v) => !v)}
              >
                <Reply className="h-3 w-3" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-destructive"
              onClick={() => deleteMutation.mutate(comment.id)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
        <p className="text-sm whitespace-pre-wrap">{comment.body}</p>
      </div>

      {showReply && (
        <div className="ml-6 space-y-2">
          <Textarea
            placeholder="Write a reply…"
            className="min-h-[64px] text-sm"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => replyMutation.mutate(replyText)}
              disabled={!replyText.trim() || replyMutation.isPending}
            >
              <Send className="h-3.5 w-3.5 mr-1" />
              Reply
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowReply(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {comment.replies?.map((r) => (
        <CommentItem key={r.id} comment={r} entityType={entityType} entityId={entityId} depth={depth + 1} />
      ))}
    </div>
  )
}

export function CommentThread({ entityType, entityId, className }: CommentThreadProps) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState("")

  const { data: comments = [], isLoading } = useQuery<Comment[]>({
    queryKey: ["comments", entityType, entityId],
    queryFn: () => apiClient.get(`/api/comments?entityType=${entityType}&entityId=${entityId}`),
  })

  const postMutation = useMutation({
    mutationFn: (body: string) =>
      apiClient.post("/api/comments", {
        entityType,
        entityId,
        body,
        authorName: user?.name ?? "Anonymous",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments", entityType, entityId] })
      setDraft("")
    },
  })

  const totalCount = comments.reduce((sum, c) => sum + 1 + (c.replies?.length ?? 0), 0)

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-1.5 text-sm font-semibold">
        <MessageSquare className="h-4 w-4 text-muted-foreground" />
        Comments {totalCount > 0 && <span className="text-muted-foreground font-normal">({totalCount})</span>}
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading comments…</p>
      ) : comments.length === 0 ? (
        <p className="text-sm text-muted-foreground">No comments yet.</p>
      ) : (
        <div className="space-y-3">
          {comments.map((c) => (
            <CommentItem key={c.id} comment={c} entityType={entityType} entityId={entityId} />
          ))}
        </div>
      )}

      <div className="space-y-2 pt-2 border-t">
        <Textarea
          placeholder="Add a comment…"
          className="min-h-[72px] text-sm"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && draft.trim()) {
              postMutation.mutate(draft.trim())
            }
          }}
        />
        <Button
          size="sm"
          onClick={() => postMutation.mutate(draft.trim())}
          disabled={!draft.trim() || postMutation.isPending}
        >
          <Send className="h-3.5 w-3.5 mr-1.5" />
          {postMutation.isPending ? "Posting…" : "Post"}
        </Button>
      </div>
    </div>
  )
}
