export type OutcomeType = 'decision' | 'action_item' | 'requirement' | 'blocker'

export type ExtractionStatus = 'none' | 'pending' | 'processing' | 'completed' | 'failed'

export interface EvidenceRef {
  segmentIndex: number
  speaker: string
  timestamp: number
  textSnippet?: string
}

export interface Outcome {
  id: string
  type: OutcomeType
  title: string
  detail: string
  confidence: number
  evidenceRefs: EvidenceRef[]
  promoted: boolean
  promotedId: string | null
}

export interface OutcomesResponse {
  jobId: string
  extractionStatus: ExtractionStatus
  outcomes: Outcome[]
}

export type TaskStatus = 'todo' | 'in_progress' | 'done'

export type TaskPriority = 'low' | 'medium' | 'high'

export interface Task {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string | null
  sourceRecordingId: string | null
  backlink: string | null
  status: TaskStatus
  priority: TaskPriority
  dueDate: string | null
  assignee: string | null
  tags: string[]
  createdAt: string
  updatedAt: string
}

export interface TaskFilters {
  status?: string | null
  search?: string | null
}

export interface CreateTaskInput {
  title: string
  detail?: string
  priority?: TaskPriority
  dueDate?: string | null
  assignee?: string | null
  tags?: string[]
}

export interface UpdateTaskInput {
  title?: string
  detail?: string
  status?: TaskStatus
  priority?: TaskPriority
  dueDate?: string | null
  assignee?: string | null
  tags?: string[]
}

export interface RequirementRecord {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string
  sourceRecordingId: string
  backlink: string
  createdAt: string
}
