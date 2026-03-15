export type MilestoneStatus = "upcoming" | "in_progress" | "completed"

export interface MilestoneProgress {
  total: number
  todo: number
  inProgress: number
  done: number
  pct: number
}

export interface MilestoneWithProgress {
  id: string
  projectId: string
  title: string
  detail: string
  startDate: string | null
  endDate: string | null
  status: MilestoneStatus
  createdBy: string | null
  createdAt: string
  updatedAt: string
  progress?: MilestoneProgress
}
