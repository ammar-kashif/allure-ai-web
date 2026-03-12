"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import type { OutcomesResponse, ExtractionStatus } from "@/types/outcome"

export function useOutcomes(
  recordingId: string,
  enabled: boolean
): UseQueryResult<OutcomesResponse> {
  return useQuery({
    queryKey: ["outcomes", recordingId],
    queryFn: () =>
      apiClient.get<OutcomesResponse>(
        `/api/recordings/${recordingId}/outcomes`
      ),
    enabled: !!recordingId && enabled,
    staleTime: 30_000,
  })
}

export function useExtractionStatus(
  recordingId: string,
  enabled: boolean
): UseQueryResult<{ extractionStatus: ExtractionStatus }> {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: ["extraction-status", recordingId],
    queryFn: async () => {
      const result = await apiClient.get<{
        status: string
        extraction_status: string
      }>(`/api/recordings/${recordingId}/status`)

      const extractionStatus = result.extraction_status as ExtractionStatus

      // When extraction completes, invalidate outcomes query to refetch
      if (extractionStatus === "completed") {
        queryClient.invalidateQueries({
          queryKey: ["outcomes", recordingId],
        })
      }

      return { extractionStatus }
    },
    enabled: !!recordingId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data
      if (
        data?.extractionStatus === "completed" ||
        data?.extractionStatus === "failed"
      ) {
        return false
      }
      return 3000
    },
  })
}

interface PromoteOutcomeVars {
  outcomeId: string
  recordingId: string
  outcomeIndex: number
}

interface PromoteOutcomeResult {
  id: string
  type: string
  backlink: string
}

export function usePromoteOutcome(): UseMutationResult<
  PromoteOutcomeResult,
  Error,
  PromoteOutcomeVars
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ outcomeId, recordingId, outcomeIndex }: PromoteOutcomeVars) =>
      apiClient.post<PromoteOutcomeResult>(
        `/api/outcomes/${outcomeId}/promote`,
        { recordingId, outcomeIndex }
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["outcomes", variables.recordingId],
      })
    },
  })
}
