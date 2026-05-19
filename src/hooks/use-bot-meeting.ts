"use client"

import {
  useMutation,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import { useBotMeetingStore } from "@/stores/bot-meeting-store"
import {
  BOT_ACTIVE_STATES,
  type BotDispatchInput,
  type BotDispatchResponse,
  type BotMeetingState,
  type BotStopResponse,
} from "@/types/meeting-bot"

/**
 * Dispatch a bot to a meeting URL. On success the session is stored in
 * bot-meeting-store so the banner shows up everywhere in the dashboard.
 */
export function useDispatchBot(): UseMutationResult<
  BotDispatchResponse,
  Error,
  BotDispatchInput
> {
  const setActive = useBotMeetingStore((s) => s.setActive)

  return useMutation({
    mutationFn: (input) =>
      apiClient.post<BotDispatchResponse>("/api/meetings/dispatch", {
        meeting_url: input.meeting_url,
        ...(input.title ? { title: input.title } : {}),
        ...(input.platform ? { platform: input.platform } : {}),
        ...(input.project_id ? { project_id: input.project_id } : {}),
      }),
    onSuccess: (data, variables) => {
      setActive({
        recordingId: data.recording_id,
        title: variables.title ?? null,
        meetingUrl: variables.meeting_url,
      })
    },
  })
}

/**
 * Poll a bot meeting's lifecycle. Polls every 3s while in an active state,
 * stops automatically when ingested / failed (handled by refetchInterval
 * returning false).
 */
export function useBotMeetingStatus(
  recordingId: string | null
): UseQueryResult<BotMeetingState> {
  return useQuery({
    queryKey: ["bot-meeting", recordingId],
    queryFn: () =>
      apiClient.get<BotMeetingState>(`/api/meetings/${recordingId}`),
    enabled: !!recordingId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 3000
      return BOT_ACTIVE_STATES.includes(data.status) ? 3000 : false
    },
  })
}

/**
 * List every meeting dispatch (newest first). Powers the Meetings tab.
 * Polls every 5 s so the table stays live as the watcher transitions
 * dispatched -> recording -> forwarding -> ingested|failed.
 */
export function useBotMeetings(): UseQueryResult<BotMeetingState[]> {
  return useQuery({
    queryKey: ["bot-meetings"],
    queryFn: () => apiClient.get<BotMeetingState[]>("/api/meetings"),
    refetchInterval: 5000,
  })
}

/**
 * Ask the bot to gracefully leave the meeting. The poller picks up the
 * resulting status flip automatically.
 */
export function useStopBotMeeting(): UseMutationResult<
  BotStopResponse,
  Error,
  string
> {
  return useMutation({
    mutationFn: (recordingId) =>
      apiClient.post<BotStopResponse>(
        `/api/meetings/${recordingId}/stop`
      ),
  })
}
