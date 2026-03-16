"use client"

import { useState } from "react"

import { useProjects, useCreateProject } from "@/hooks/use-projects"

interface ProjectAssignmentProps {
  recordingId: string
  currentProjectId: string | null
  onAssign: (projectId: string) => void
}

export function ProjectAssignment({
  recordingId: _recordingId,
  currentProjectId,
  onAssign,
}: ProjectAssignmentProps) {
  const { data: projects = [] } = useProjects()
  const createProject = useCreateProject()
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")

  // If already assigned, show project name as static text
  if (currentProjectId) {
    const project = projects.find((p) => p.id === currentProjectId)
    return (
      <span className="text-sm text-muted-foreground">
        {project?.name ?? "Unknown Project"}
      </span>
    )
  }

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return
    try {
      const project = await createProject.mutateAsync({
        name: newProjectName.trim(),
      })
      setNewProjectName("")
      setIsCreating(false)
      onAssign(project.id)
    } catch {
      // Error handled by mutation
    }
  }

  if (isCreating) {
    return (
      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <input
          type="text"
          value={newProjectName}
          onChange={(e) => setNewProjectName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleCreateProject()
            if (e.key === "Escape") setIsCreating(false)
          }}
          placeholder="Project name..."
          className="h-7 w-32 rounded border border-input bg-background px-2 text-xs outline-none focus:ring-1 focus:ring-ring"
          autoFocus
        />
        <button
          onClick={handleCreateProject}
          disabled={!newProjectName.trim() || createProject.isPending}
          className="h-7 rounded bg-primary px-2 text-xs text-primary-foreground disabled:opacity-50"
        >
          {createProject.isPending ? "..." : "Create"}
        </button>
        <button
          onClick={() => setIsCreating(false)}
          className="h-7 rounded px-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div onClick={(e) => e.stopPropagation()}>
      <select
        defaultValue=""
        onChange={(e) => {
          const value = e.target.value
          if (value === "__create__") {
            setIsCreating(true)
          } else if (value) {
            onAssign(value)
          }
        }}
        className="h-7 w-36 cursor-pointer rounded border border-input bg-background px-1.5 text-xs outline-none focus:ring-1 focus:ring-ring"
        data-testid="project-select"
      >
        <option value="" disabled>
          Assign project...
        </option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
        <option value="__create__">+ Create new project</option>
      </select>
    </div>
  )
}
