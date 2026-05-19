"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useDispatchBot } from "@/hooks/use-bot-meeting"

interface BotDispatchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const SUPPORTED_HOSTS = [
  "meet.google.com",
  "teams.microsoft.com",
  "teams.live.com",
  "zoom.us",
  "zoom.com",
]

function isLikelyMeetingUrl(value: string): boolean {
  if (!value) return false
  try {
    const url = new URL(value)
    return SUPPORTED_HOSTS.some((h) => url.host.includes(h))
  } catch {
    return false
  }
}

export function BotDispatchDialog({
  open,
  onOpenChange,
}: BotDispatchDialogProps) {
  const [meetingUrl, setMeetingUrl] = useState("")
  const [title, setTitle] = useState("")

  const dispatch = useDispatchBot()
  const urlValid = isLikelyMeetingUrl(meetingUrl)

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!urlValid || dispatch.isPending) return

    dispatch.mutate(
      {
        meeting_url: meetingUrl.trim(),
        title: title.trim() || null,
      },
      {
        onSuccess: () => {
          toast.success("Bot dispatched to meeting", {
            description: "Admit the bot from the meeting host UI when it joins.",
          })
          setMeetingUrl("")
          setTitle("")
          onOpenChange(false)
        },
        onError: (err) => {
          toast.error("Could not dispatch bot", {
            description: err.message || "Backend or bot service unavailable.",
          })
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Send a bot to a meeting</DialogTitle>
          <DialogDescription>
            Paste a Google Meet, Microsoft Teams, or Zoom link. The bot
            joins as a participant and feeds the recording into Allure
            automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="meeting-url">Meeting URL</Label>
            <Input
              id="meeting-url"
              type="url"
              autoComplete="off"
              placeholder="https://meet.google.com/abc-defg-hij"
              value={meetingUrl}
              onChange={(e) => setMeetingUrl(e.target.value)}
              disabled={dispatch.isPending}
              required
            />
            {meetingUrl && !urlValid ? (
              <p className="text-xs text-muted-foreground">
                URL must be from {SUPPORTED_HOSTS.slice(0, 3).join(", ")}, …
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="meeting-title">Title (optional)</Label>
            <Input
              id="meeting-title"
              type="text"
              autoComplete="off"
              placeholder="Sprint sync"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={dispatch.isPending}
              maxLength={80}
            />
            <p className="text-xs text-muted-foreground">
              Shown to other participants as the bot&rsquo;s display name.
              Defaults to <code>Allure-XXXXXXXX</code>.
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={dispatch.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!urlValid || dispatch.isPending}
            >
              {dispatch.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Dispatching…
                </>
              ) : (
                "Send bot"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
