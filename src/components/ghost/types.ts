export type GhostCitation = {
  source_type: "segment" | "attachment" | "outcome"
  recording_id?: string
  segment_index?: number
  timestamp?: number
  speaker?: string
  text?: string
  attachment_id?: string
  filename?: string
  snippet?: string
  outcome_id?: string
  type?: string
  title?: string
  detail?: string
}

export type GhostPersistedToolCall = {
  name: string
  arguments: Record<string, unknown>
  arguments_summary?: Record<string, unknown>
  summary?: string
  result_preview?: unknown
  error?: string | null
}

export type GhostMessage = {
  id: string
  conv_id: string
  role: "user" | "assistant" | "tool"
  content: string
  citations?: GhostCitation[]
  tool_calls?: GhostPersistedToolCall[]
  tokens_in?: number
  tokens_out?: number
  cost_usd?: number
  latency_ms?: number
  created_at: string
}

export type GhostConversation = {
  id: string
  title: string | null
  project_id: string | null
  created_at: string
  last_activity_at: string
  messages?: GhostMessage[]
}

export type GhostAskResponse = {
  conv_id: string
  answer: string
  citations: GhostCitation[]
  triage: { scope: string; intent: string; can_spawn_subagents: boolean }
  tokens_in: number
  tokens_out: number
  cost_usd: number
  latency_ms: number
  tool_calls: Array<{ name: string; arguments: Record<string, unknown>; error?: string | null }>
}

export type GhostSettings = {
  mode: "hosted" | "local"
  provider: "anthropic" | "openai" | "custom"
  model: string
  monthly_cap_usd: number
  base_url?: string | null
  api_key_set: boolean
  updated_at: string
}

export type GhostCost = {
  month_to_date_usd: number
  monthly_cap_usd: number
}

export type GhostStreamEvent =
  | { kind: "triage"; intent: string; scope: string; can_spawn_subagents: boolean }
  | { kind: "tool.start"; name: string; arguments?: Record<string, unknown> }
  | { kind: "tool.done"; name: string; summary?: string; error?: boolean }
  | { kind: "subagent.spawning"; task_count: number; questions: string[] }
  | { kind: "subagent.started"; question: string }
  | { kind: "subagent.done"; question: string; error?: string }
  | { kind: "final"; conv_id: string; answer: string; citations: GhostCitation[]; cost_usd: number; latency_ms: number; tokens_in: number; tokens_out: number; tool_calls: Array<{ name: string; arguments: Record<string, unknown> }> }
  | { kind: "error"; message: string }
  | { kind: "heartbeat" }
