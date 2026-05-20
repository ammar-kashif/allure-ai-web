export type AutonomyActionKind =
  | "task_created"
  | "task_discussed"
  | "task_appears_done"
  | "task_appears_blocked"
  | "skipped_duplicate"
  | "skipped_verifier"
  | "skipped_gate"

export type AutonomyAction = {
  id: string
  run_id: string
  recording_id: string
  kind: AutonomyActionKind
  target_task_id: string | null
  segment_index: number | null
  speaker: string | null
  reason: string
  verifier_reason: string | null
  detector_payload: Record<string, unknown>
  reversed_at: string | null
  created_at: string
}

export type AutonomyRun = {
  id: string
  recording_id: string
  project_id: string | null
  status: "running" | "completed" | "failed" | "skipped"
  skip_reason: string | null
  detect_tokens_in: number | null
  detect_tokens_out: number | null
  verify_tokens_in: number | null
  verify_tokens_out: number | null
  cost_usd: number | null
  tasks_created: number
  tasks_discussed: number
  follow_up_to: string[]
  error: string | null
  created_at: string
  completed_at: string | null
}

export type AutonomyResponse = {
  run: AutonomyRun | null
  actions: AutonomyAction[]
}

export type AutonomySettings = {
  enabled: boolean
  monthly_cap_usd: number
  disabled_project_ids: string[]
}

export type AutonomyCost = {
  month_to_date_usd: number
  monthly_cap_usd: number
}
