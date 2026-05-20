"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import type {
  AutonomyCost,
  AutonomyResponse,
  AutonomySettings,
} from "@/components/autonomy/types"

export function useAutonomyRun(recordingId: string) {
  return useQuery({
    queryKey: ["autonomy", recordingId],
    queryFn: () =>
      apiClient.get<AutonomyResponse>(`/api/recordings/${recordingId}/autonomy`),
  })
}

export function useUndoAutonomyAction(recordingId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (actionId: string) =>
      apiClient.post<{ reversed: boolean }>(
        `/api/autonomy/actions/${actionId}/undo`,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["autonomy", recordingId] })
      qc.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useUndoAutonomyRun(recordingId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) =>
      apiClient.post<{ reversed_count: number }>(
        `/api/autonomy/runs/${runId}/undo`,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["autonomy", recordingId] })
      qc.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useAutonomySettings() {
  return useQuery({
    queryKey: ["autonomy-settings"],
    queryFn: () => apiClient.get<AutonomySettings>("/api/autonomy/settings"),
  })
}

export function useUpdateAutonomySettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<AutonomySettings>) =>
      apiClient.patch<AutonomySettings>("/api/autonomy/settings", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["autonomy-settings"] })
    },
  })
}

export function useAutonomyCost() {
  return useQuery({
    queryKey: ["autonomy-cost"],
    queryFn: () => apiClient.get<AutonomyCost>("/api/autonomy/cost"),
    refetchInterval: 30_000,
  })
}
