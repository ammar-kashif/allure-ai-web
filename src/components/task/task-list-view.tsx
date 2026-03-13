"use client"

import { useState, useDeferredValue } from "react"
import { Search, Plus } from "lucide-react"
import { format, parseISO } from "date-fns"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table"
import { TaskPriorityBadge } from "@/components/task/task-priority-badge"
import { useTasks } from "@/hooks/use-tasks"
import type { Task, TaskStatus } from "@/types/outcome"

const STATUS_TABS = [
  { value: "all", label: "All" },
  { value: "todo", label: "To Do" },
  { value: "in_progress", label: "In Progress" },
  { value: "done", label: "Done" },
] as const

const statusBadgeConfig: Record<TaskStatus, { label: string; className: string }> = {
  todo: { label: "To Do", className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
  in_progress: { label: "In Progress", className: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400" },
  done: { label: "Done", className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" },
}

interface TaskListViewProps {
  onTaskClick: (task: Task) => void
  onCreateClick: () => void
}

export function TaskListView({ onTaskClick, onCreateClick }: TaskListViewProps) {
  const [activeTab, setActiveTab] = useState("all")
  const [query, setQuery] = useState("")
  const deferredQuery = useDeferredValue(query)

  const searchFilter = deferredQuery || null

  // Single query for all tasks (with search filter only) — derive filtered list and counts client-side
  const { data: allTasks = [], isLoading } = useTasks({ search: searchFilter })

  const counts = {
    all: allTasks.length,
    todo: allTasks.filter((t) => t.status === "todo").length,
    in_progress: allTasks.filter((t) => t.status === "in_progress").length,
    done: allTasks.filter((t) => t.status === "done").length,
  }

  const tasks = activeTab === "all"
    ? allTasks
    : allTasks.filter((t) => t.status === activeTab)

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "--"
    try {
      return format(parseISO(dateStr), "MMM d, yyyy")
    } catch {
      return "--"
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  const renderTable = (taskList: Task[]) => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead>Due Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {taskList.length === 0 ? (
          <TableRow>
            <TableCell colSpan={4} className="py-16 text-center">
              <div className="flex flex-col items-center gap-3">
                <p className="text-base text-muted-foreground">No tasks yet</p>
                <Button variant="outline" size="sm" onClick={onCreateClick}>
                  <Plus className="mr-1 h-4 w-4" />
                  New Task
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ) : (
          taskList.map((task) => {
            const statusConfig = statusBadgeConfig[task.status]
            return (
              <TableRow
                key={task.id}
                className="cursor-pointer"
                onClick={() => onTaskClick(task)}
              >
                <TableCell className="font-medium">{task.title}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className={statusConfig.className}>
                    {statusConfig.label}
                  </Badge>
                </TableCell>
                <TableCell>
                  <TaskPriorityBadge priority={task.priority} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(task.dueDate)}
                </TableCell>
              </TableRow>
            )
          })
        )}
      </TableBody>
    </Table>
  )

  return (
    <div className="space-y-4">
      {/* Search bar and create button */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tasks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button onClick={onCreateClick} size="sm">
          <Plus className="mr-1 h-4 w-4" />
          New Task
        </Button>
      </div>

      {/* Status tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {STATUS_TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
              <span className="ml-1 text-xs text-muted-foreground">
                ({counts[tab.value as keyof typeof counts]})
              </span>
            </TabsTrigger>
          ))}
        </TabsList>

        {STATUS_TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            {renderTable(tasks)}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
