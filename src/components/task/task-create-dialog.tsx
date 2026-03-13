"use client"

import { useState } from "react"
import { toast } from "sonner"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useCreateTask } from "@/hooks/use-tasks"

interface TaskCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskCreateDialog({ open, onOpenChange }: TaskCreateDialogProps) {
  const [title, setTitle] = useState("")
  const [showDetails, setShowDetails] = useState(false)
  const [detail, setDetail] = useState("")
  const createTask = useCreateTask()

  const handleSubmit = () => {
    const trimmed = title.trim()
    if (!trimmed) return

    createTask.mutate(
      { title: trimmed, detail: detail.trim() || undefined },
      {
        onSuccess: () => {
          setTitle("")
          setDetail("")
          setShowDetails(false)
          onOpenChange(false)
        },
        onError: (error) => {
          toast.error("Failed to create task", {
            description: error.message,
          })
        },
      }
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          setTitle("")
          setDetail("")
          setShowDetails(false)
        }
        onOpenChange(nextOpen)
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Task</DialogTitle>
          <DialogDescription>
            Create a new task. Only a title is required.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="task-title">Title</Label>
            <Input
              id="task-title"
              placeholder="What needs to be done?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
          </div>

          {showDetails ? (
            <div className="space-y-2">
              <Label htmlFor="task-detail">Details</Label>
              <Textarea
                id="task-detail"
                placeholder="Add more details..."
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                className="min-h-20"
              />
            </div>
          ) : (
            <button
              type="button"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setShowDetails(true)}
            >
              + Add details
            </button>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={!title.trim() || createTask.isPending}
          >
            {createTask.isPending ? "Creating..." : "Create Task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
