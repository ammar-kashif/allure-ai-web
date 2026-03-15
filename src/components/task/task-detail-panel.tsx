"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { ExternalLink } from "lucide-react"
import { toast } from "sonner"

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { useTasks, useUpdateTask, useDeleteTask } from "@/hooks/use-tasks"
import type { Task, TaskStatus, TaskPriority, UpdateTaskInput } from "@/types/outcome"

interface TaskDetailPanelProps {
  taskId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskDetailPanel({ taskId, open, onOpenChange }: TaskDetailPanelProps) {
  const { data: tasks = [] } = useTasks()
  const updateTask = useUpdateTask()
  const deleteTask = useDeleteTask()

  const task = tasks.find((t) => t.id === taskId) ?? null

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  // Local state for editable fields
  const [title, setTitle] = useState("")
  const [detail, setDetail] = useState("")
  const [assignee, setAssignee] = useState("")
  const [tagsInput, setTagsInput] = useState("")
  const [dueDate, setDueDate] = useState("")

  // Debounce ref for title
  const titleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync local state when task changes
  useEffect(() => {
    if (task) {
      setTitle(task.title)
      setDetail(task.detail || "")
      setAssignee(task.assignee || "")
      setTagsInput(task.tags?.join(", ") || "")
      setDueDate(task.dueDate || "")
    }
  }, [task])

  const handleUpdate = useCallback(
    (data: UpdateTaskInput) => {
      if (!taskId) return
      updateTask.mutate({ id: taskId, ...data })
    },
    [taskId, updateTask]
  )

  const handleTitleChange = (value: string) => {
    setTitle(value)
    if (titleTimeoutRef.current) clearTimeout(titleTimeoutRef.current)
    titleTimeoutRef.current = setTimeout(() => {
      if (value.trim() && value.trim() !== task?.title) {
        handleUpdate({ title: value.trim() })
      }
    }, 500)
  }

  const handleTitleBlur = () => {
    if (titleTimeoutRef.current) {
      clearTimeout(titleTimeoutRef.current)
      titleTimeoutRef.current = null
    }
    if (title.trim() && title.trim() !== task?.title) {
      handleUpdate({ title: title.trim() })
    }
  }

  const handleStatusChange = (value: string | null) => {
    if (value) handleUpdate({ status: value as TaskStatus })
  }

  const handlePriorityChange = (value: string | null) => {
    if (value) handleUpdate({ priority: value as TaskPriority })
  }

  const handleDueDateChange = (value: string) => {
    setDueDate(value)
    handleUpdate({ dueDate: value || null })
  }

  const handleAssigneeBlur = () => {
    if (assignee !== (task?.assignee || "")) {
      handleUpdate({ assignee: assignee.trim() || null })
    }
  }

  const handleTagsBlur = () => {
    const parsed = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
    const currentTags = task?.tags || []
    if (JSON.stringify(parsed) !== JSON.stringify(currentTags)) {
      handleUpdate({ tags: parsed })
    }
  }

  const handleDetailBlur = () => {
    if (detail !== (task?.detail || "")) {
      handleUpdate({ detail: detail })
    }
  }

  const handleDelete = () => {
    if (!taskId) return
    deleteTask.mutate(taskId, {
      onSuccess: () => {
        setDeleteConfirmOpen(false)
        onOpenChange(false)
      },
      onError: (error) => {
        toast.error("Failed to delete task", { description: error.message })
      },
    })
  }

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (titleTimeoutRef.current) clearTimeout(titleTimeoutRef.current)
    }
  }, [])

  if (!task) return null

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="overflow-y-auto sm:max-w-md">
          <SheetHeader>
            <SheetTitle className="sr-only">Task Details</SheetTitle>
            <SheetDescription className="sr-only">
              Edit task fields. Changes save automatically.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-5 p-4 pt-0">
            {/* Title - inline editable */}
            <div>
              <Input
                value={title}
                onChange={(e) => handleTitleChange(e.target.value)}
                onBlur={handleTitleBlur}
                className="border-none px-0 text-lg font-semibold shadow-none focus-visible:ring-0 focus-visible:border-none focus-visible:shadow-none"
                placeholder="Task title"
              />
            </div>

            {/* Status */}
            <div className="space-y-1.5">
              <Label>Status</Label>
              <Select value={task.status} onValueChange={handleStatusChange}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">To Do</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Priority */}
            <div className="space-y-1.5">
              <Label>Priority</Label>
              <Select value={task.priority} onValueChange={handlePriorityChange}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Due Date */}
            <div className="space-y-1.5">
              <Label htmlFor="task-due-date">Due Date</Label>
              <Input
                id="task-due-date"
                type="date"
                value={dueDate}
                onChange={(e) => handleDueDateChange(e.target.value)}
              />
            </div>

            {/* Assignee */}
            <div className="space-y-1.5">
              <Label htmlFor="task-assignee">Assignee</Label>
              <Input
                id="task-assignee"
                placeholder="Unassigned"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                onBlur={handleAssigneeBlur}
              />
            </div>

            {/* Tags */}
            <div className="space-y-1.5">
              <Label htmlFor="task-tags">Tags</Label>
              <Input
                id="task-tags"
                placeholder="Comma-separated tags"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                onBlur={handleTagsBlur}
              />
            </div>

            {/* Detail / Notes */}
            <div className="space-y-1.5">
              <Label htmlFor="task-detail">Notes</Label>
              <Textarea
                id="task-detail"
                placeholder="Add notes..."
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                onBlur={handleDetailBlur}
                className="min-h-24"
              />
            </div>

            {/* Source section */}
            {task.sourceRecordingId && (
              <div className="space-y-1.5 border-t pt-4">
                <p className="text-xs font-medium text-muted-foreground">Source</p>
                {task.backlink && (
                  <p className="text-sm text-muted-foreground">{task.backlink}</p>
                )}
                <Link
                  href={`/recordings/${task.sourceRecordingId}${task.sourceHighlightIndex !== null ? `?highlight=${task.sourceHighlightIndex}` : ""}`}
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                  onClick={() => onOpenChange(false)}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  View in transcript
                </Link>
              </div>
            )}

            {/* Delete button */}
            <div className="border-t pt-4">
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setDeleteConfirmOpen(true)}
              >
                Delete Task
              </Button>
            </div>
          </div>

          <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this task?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleteTask.isPending}
                >
                  {deleteTask.isPending ? "Deleting..." : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </SheetContent>
      </Sheet>
    </>
  )
}
