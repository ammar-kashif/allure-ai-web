"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query"

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
): UseQueryResult<{ status: RecordingStatus }> {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: ["recording-status", id],
    queryFn: async () => {
      const result = await apiClient.get<{ status: RecordingStatus }>(
        `/api/recordings/${id}/status`
      )

      // When status changes to ready or error, invalidate recordings list
      if (result.status === "ready" || result.status === "error") {
        queryClient.invalidateQueries({ queryKey: ["recordings"] })
        queryClient.invalidateQueries({ queryKey: ["recording", id] })
      }

      return result
    },
    enabled,
    refetchInterval: (query) => {
      const data = query.state.data
      // Stop polling when status is ready or error
      if (data?.status === "ready" || data?.status === "error") {
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

export function useAssignProject(): UseMutationResult<
  Recording,
  Error,
  { recordingId: string; projectId: string; file?: Blob }
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      recordingId,
      projectId,
    }: {
      recordingId: string
      projectId: string
      file?: Blob
    }) => {
      // PATCH to assign project and trigger upload
      const updated = await apiClient.patch<Recording>(
        `/api/recordings/${recordingId}`,
        { projectId, status: "processing" }
      )
      return updated
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      queryClient.invalidateQueries({
        queryKey: ["recording", variables.recordingId],
      })
    },
  })
}
