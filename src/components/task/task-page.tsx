"use client"

import { useState } from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { TaskListView } from "@/components/task/task-list-view"
import { TaskKanbanView } from "@/components/task/task-kanban-view"
import { TaskCreateDialog } from "@/components/task/task-create-dialog"
import { TaskDetailPanel } from "@/components/task/task-detail-panel"
import type { Task } from "@/types/outcome"

export function TaskPage() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)

  const handleTaskClick = (task: Task) => {
    setSelectedTaskId(task.id)
  }

  const handleCreateClick = () => {
    setCreateDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-2xl font-bold tracking-tight">Tasks</h1>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">List</TabsTrigger>
          <TabsTrigger value="board">Board</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <TaskListView
            onTaskClick={handleTaskClick}
            onCreateClick={handleCreateClick}
          />
        </TabsContent>

        <TabsContent value="board">
          <TaskKanbanView
            onTaskClick={handleTaskClick}
            onCreateClick={handleCreateClick}
          />
        </TabsContent>
      </Tabs>

      <TaskCreateDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />

      <TaskDetailPanel
        taskId={selectedTaskId}
        open={selectedTaskId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedTaskId(null)
        }}
      />
    </div>
  )
}
