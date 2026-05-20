"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query"

import { toast } from "sonner"

import { apiClient } from "@/lib/api/client"
import type { Recording, RecordingStatus, Transcript } from "@/types/recording"

export function useRecordings(
  status?: RecordingStatus
): UseQueryResult<Recording[]> {
  const params = status ? `?status=${status}` : ""
  return useQuery({
    queryKey: ["recordings", status ?? "all"],
    queryFn: () => apiClient.get<Recording[]>(`/api/recordings${params}`),
  })
}

export function useRecording(id: string): UseQueryResult<Recording> {
  return useQuery({
    queryKey: ["recording", id],
    queryFn: () => apiClient.get<Recording>(`/api/recordings/${id}`),
    enabled: !!id,
  })
}

export function useRecordingStatus(
  id: string,
  enabled: boolean
): UseQueryResult<{ status: RecordingStatus; extraction_status?: string }> {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: ["recording-status", id],
    queryFn: async () => {
      const result = await apiClient.get<{
        status: RecordingStatus
        extraction_status?: string
      }>(`/api/recordings/${id}/status`)

      // When status changes to ready or error, invalidate recordings list
      if (result.status === "ready" || result.status === "error") {
        queryClient.invalidateQueries({ queryKey: ["recordings"] })
        queryClient.invalidateQueries({ queryKey: ["recording", id] })
      }
      // When extraction completes, the backend has just pushed the new
      // title/description into the local DB. Re-pull both single-recording
      // and list queries so the page header AND the meetings list update
      // without a manual refresh.
      if (result.extraction_status === "completed") {
        queryClient.invalidateQueries({ queryKey: ["recordings"] })
        queryClient.invalidateQueries({ queryKey: ["recording", id] })
        queryClient.invalidateQueries({ queryKey: ["transcript", id] })
      }

      return result
    },
    enabled,
    refetchInterval: (query) => {
      const data = query.state.data
      // Only stop polling once extraction has truly settled. Treating
      // "none" as settled was a bug — the backend has a brief window
      // where status="ready" + extraction_status="none" before extract
      // is queued, and stopping there meant the title never refreshed.
      const extractionSettled =
        data?.extraction_status === "completed" ||
        data?.extraction_status === "failed"
      if (
        (data?.status === "ready" || data?.status === "error") &&
        extractionSettled
      ) {
        return false
      }
      return 3000
    },
  })
}

export function useTranscript(
  recordingId: string,
  enabled: boolean
): UseQueryResult<Transcript> {
  return useQuery({
    queryKey: ["transcript", recordingId],
    queryFn: () =>
      apiClient.get<Transcript>(`/api/recordings/${recordingId}/transcript`),
    enabled: !!recordingId && enabled,
    staleTime: Infinity,
  })
}

export function useUploadRecording(): UseMutationResult<
  Recording,
  Error,
  FormData
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (formData: FormData) =>
      apiClient.post<Recording>("/api/recordings", formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
    },
  })
}

export function useRenameRecording(): UseMutationResult<
  Recording,
  Error,
  { recordingId: string; title: string }
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ recordingId, title }: { recordingId: string; title: string }) =>
      apiClient.patch<Recording>(`/api/recordings/${recordingId}`, { title }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      queryClient.invalidateQueries({
        queryKey: ["recording", variables.recordingId],
      })
    },
  })
}

export function useDeleteRecording(): UseMutationResult<
  void,
  Error,
  string
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (recordingId: string) =>
      apiClient.delete<void>(`/api/recordings/${recordingId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
    },
  })
}

export function useReprocessRecording(): UseMutationResult<
  void,
  Error,
  string
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (recordingId: string) =>
      apiClient.post<void>(`/api/recordings/${recordingId}/reprocess`, {}),
    onSuccess: (_data, recordingId) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      queryClient.invalidateQueries({ queryKey: ["recording", recordingId] })
      queryClient.invalidateQueries({ queryKey: ["transcript", recordingId] })
      // Also bust the polling/cache for extraction-status and outcomes —
      // otherwise the sticky "completed" cache from the previous run stops
      // the polling and the OutcomesTab never sees the new extraction round.
      queryClient.invalidateQueries({
        queryKey: ["recording-status", recordingId],
      })
      queryClient.invalidateQueries({
        queryKey: ["extraction-status", recordingId],
      })
      queryClient.invalidateQueries({ queryKey: ["outcomes", recordingId] })
    },
  })
}

export function useAssignProject(): UseMutationResult<
  Recording,
  Error,
  { recordingId: string; projectId: string; file?: Blob }
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      recordingId,
      projectId,
    }: {
      recordingId: string
      projectId: string
      file?: Blob
    }) =>
      apiClient.patch<Recording>(`/api/recordings/${recordingId}`, {
        projectId,
        status: "processing",
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      queryClient.invalidateQueries({
        queryKey: ["recording", variables.recordingId],
      })
    },
  })
}

export function useUpdateSpeaker(): UseMutationResult<
  { ok: boolean },
  Error,
  { recordingId: string; speakerLabel: string; customLabel?: string; role?: string }
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ recordingId, speakerLabel, customLabel, role }) => {
      const body: Record<string, unknown> = {}
      if (customLabel !== undefined) body.custom_label = customLabel
      if (role !== undefined) body.role = role
      return apiClient.patch<{ ok: boolean }>(
        `/api/recordings/${recordingId}/speakers/${encodeURIComponent(speakerLabel)}`,
        body
      )
    },
    onMutate: async ({ recordingId, speakerLabel, customLabel, role }) => {
      // Cancel outgoing transcript refetches
      await queryClient.cancelQueries({ queryKey: ["transcript", recordingId] })

      // Snapshot previous value
      const previous = queryClient.getQueryData<Transcript>(["transcript", recordingId])

      // Optimistically update the cached transcript
      if (previous?.speakers) {
        queryClient.setQueryData<Transcript>(["transcript", recordingId], {
          ...previous,
          speakers: previous.speakers.map((s) =>
            s.label === speakerLabel
              ? {
                  ...s,
                  ...(customLabel !== undefined ? { customLabel } : {}),
                  ...(role !== undefined ? { role } : {}),
                }
              : s
          ),
        })
      }

      return { previous }
    },
    onError: (_err, { recordingId }, context) => {
      // Revert to snapshot on error
      if (context?.previous) {
        queryClient.setQueryData(["transcript", recordingId], context.previous)
      }
      toast.error("Failed to update speaker")
    },
    onSettled: (_data, _error, { recordingId }) => {
      // Refetch transcript to sync with backend
      queryClient.invalidateQueries({ queryKey: ["transcript", recordingId] })
    },
  })
}
