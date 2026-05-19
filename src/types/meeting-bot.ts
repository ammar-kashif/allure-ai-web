export type BotMeetingStatus =
  | "dispatched"
  | "recording"
  | "stop_requested"
  | "forwarding"
  | "ingested"
  | "failed"

export type BotMeetingPlatform = "google" | "microsoft" | "zoom"

export interface BotDispatchInput {
  meeting_url: string
  title?: string | null
  project_id?: string | null
  platform?: BotMeetingPlatform | null
}

export interface BotDispatchResponse {
  recording_id: string
  status: BotMeetingStatus
  platform: BotMeetingPlatform
  bot_response: Record<string, unknown>
}

export interface BotMeetingState {
  recording_id: string
  meeting_url: string
  platform: BotMeetingPlatform
  project_id: string | null
  title: string | null
  status: BotMeetingStatus
  audio_path: string | null
  dispatched_at: string
  finalized_at: string | null
  error: string | null
}

export interface BotStopResponse {
  recording_id: string
  bot_response: Record<string, unknown>
}

/** Statuses where the bot is still doing something we can poll on. */
export const BOT_ACTIVE_STATES: BotMeetingStatus[] = [
  "dispatched",
  "recording",
  "stop_requested",
  "forwarding",
]
