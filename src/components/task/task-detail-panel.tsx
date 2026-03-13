"use client"

interface TaskDetailPanelProps {
  taskId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskDetailPanel({ taskId, open, onOpenChange }: TaskDetailPanelProps) {
  if (!open || !taskId) return null
  return null
}
