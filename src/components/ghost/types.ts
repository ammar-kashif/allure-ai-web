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

export type GhostMessage = {
  id: string
  conv_id: string
  role: "user" | "assistant" | "tool"
  content: string
  citations?: GhostCitation[]
  tool_calls?: Array<{ name: string; arguments: Record<string, unknown> }>
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
