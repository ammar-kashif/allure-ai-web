"use client"

import { useDroppable } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { TaskKanbanCard } from "@/components/task/task-kanban-card"
import type { Task, TaskStatus } from "@/types/outcome"

interface TaskKanbanColumnProps {
  status: TaskStatus
  title: string
  tasks: Task[]
  onTaskClick: (task: Task) => void
}

export function TaskKanbanColumn({ status, title, tasks, onTaskClick }: TaskKanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div
      className={`flex-1 min-w-[280px] rounded-lg bg-muted/30 p-3 transition-colors ${
        isOver ? "bg-muted/50 ring-2 ring-primary/20" : ""
      }`}
    >
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
          {tasks.length}
        </span>
      </div>

      <div ref={setNodeRef} className="min-h-[200px] space-y-2">
        <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <TaskKanbanCard key={task.id} task={task} onTaskClick={onTaskClick} />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <p className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No tasks
          </p>
        )}
      </div>
    </div>
  )
}

