"use client"

import { useMemo, useState, useCallback } from "react"
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core"
import { useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TaskKanbanColumn } from "@/components/task/task-kanban-column"
import { TaskKanbanCard } from "@/components/task/task-kanban-card"
import { useTasks, useUpdateTask } from "@/hooks/use-tasks"
import type { Task, TaskStatus } from "@/types/outcome"

const COLUMNS: { status: TaskStatus; title: string }[] = [
  { status: "todo", title: "To Do" },
  { status: "in_progress", title: "In Progress" },
  { status: "done", title: "Done" },
]

const STATUS_SET = new Set<string>(["todo", "in_progress", "done"])

interface TaskKanbanViewProps {
  onTaskClick: (task: Task) => void
  onCreateClick: () => void
}

export function TaskKanbanView({ onTaskClick, onCreateClick }: TaskKanbanViewProps) {
  const { data: tasks = [] } = useTasks()
  const updateTask = useUpdateTask()
  const queryClient = useQueryClient()
  const [activeId, setActiveId] = useState<string | null>(null)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const grouped = useMemo(() => {
    const map: Record<TaskStatus, Task[]> = {
      todo: [],
      in_progress: [],
      done: [],
    }
    for (const task of tasks) {
      map[task.status]?.push(task)
    }
    return map
  }, [tasks])

  const activeTask = useMemo(
    () => (activeId ? tasks.find((t) => t.id === activeId) ?? null : null),
    [activeId, tasks]
  )

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      setActiveId(null)

      if (!over) return

      const draggedTaskId = active.id as string
      const draggedTask = tasks.find((t) => t.id === draggedTaskId)
      if (!draggedTask) return

      // Determine target status
      let targetStatus: TaskStatus | null = null

      if (STATUS_SET.has(over.id as string)) {
        // Dropped directly on a column
        targetStatus = over.id as TaskStatus
      } else {
        // Dropped on another card -- find that card's status
        const overTask = tasks.find((t) => t.id === over.id)
        if (overTask) {
          targetStatus = overTask.status
        }
      }

      if (!targetStatus || targetStatus === draggedTask.status) return

      // Optimistic update: mutate cache immediately
      queryClient.setQueryData<Task[]>(["tasks", "all"], (old) =>
        old?.map((t) =>
          t.id === draggedTaskId ? { ...t, status: targetStatus } : t
        )
      )

      updateTask.mutate(
        { id: draggedTaskId, status: targetStatus },
        {
          onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] })
          },
        }
      )
    },
    [tasks, updateTask, queryClient]
  )

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={onCreateClick}>
          <Plus className="mr-1 h-4 w-4" />
          New Task
        </Button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-2">
          {COLUMNS.map((col) => (
            <TaskKanbanColumn
              key={col.status}
              status={col.status}
              title={col.title}
              tasks={grouped[col.status]}
              onTaskClick={onTaskClick}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTask ? (
            <TaskKanbanCard task={activeTask} onTaskClick={() => {}} overlay />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
