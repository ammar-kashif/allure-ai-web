export type LogStatus = "start" | "done" | "failed"

export interface LogEvent {
  id: string
  created_at: string
  level: string
  category: string
  event: string
  status: LogStatus
  message: string
  recording_id: string | null
  job_id: string | null
  dispatch_id: string | null
  duration_ms: number | null
  metadata: Record<string, unknown>
}

export interface LogFilters {
  limit?: number
  category?: string
  status?: string
  recording_id?: string
  job_id?: string
  dispatch_id?: string
}
