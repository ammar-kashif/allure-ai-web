"use client"

interface TaskCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskCreateDialog({ open, onOpenChange }: TaskCreateDialogProps) {
  if (!open) return null
  return null
}
