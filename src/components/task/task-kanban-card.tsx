"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { format } from "date-fns"
import type { Task, TaskPriority } from "@/types/outcome"

const priorityColors: Record<TaskPriority, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-green-500",
}

interface TaskKanbanCardProps {
  task: Task
  onTaskClick: (task: Task) => void
  /** When true, renders without sortable (for DragOverlay) */
  overlay?: boolean
}

export function TaskKanbanCard({ task, onTaskClick, overlay }: TaskKanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.id,
    data: { status: task.status },
    disabled: overlay,
  })

  const style = overlay
    ? undefined
    : {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }

  return (
    <div
      ref={overlay ? undefined : setNodeRef}
      style={style}
      {...(overlay ? {} : attributes)}
      {...(overlay ? {} : listeners)}
      className="cursor-grab rounded-lg border bg-card p-3 shadow-sm hover:shadow-md transition-shadow active:cursor-grabbing"
      onClick={(e) => {
        // Only trigger click if not dragging
        if (!isDragging) {
          e.stopPropagation()
          onTaskClick(task)
        }
      }}
    >
      <div className="flex items-start gap-2">
        <span
          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${priorityColors[task.priority]}`}
          title={`${task.priority} priority`}
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium leading-snug truncate">{task.title}</p>
          {task.dueDate && (
            <p className="mt-1 text-xs text-muted-foreground">
              {format(new Date(task.dueDate), "MMM d")}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
