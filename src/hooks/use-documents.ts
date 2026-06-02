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
import type { Document } from "@/lib/db/documents"

export function useDocuments(type?: string): UseQueryResult<Document[]> {
  const params = type ? `?type=${type}` : ""
  return useQuery({
    queryKey: ["documents", type ?? "all"],
    queryFn: () => apiClient.get<Document[]>(`/api/documents${params}`),
  })
}

export function useDocumentsByRecording(
  recordingId: string,
  enabled = true
): UseQueryResult<Document[]> {
  return useQuery({
    queryKey: ["documents", "recording", recordingId],
    queryFn: () =>
      apiClient.get<Document[]>(
        `/api/documents?sourceRecordingId=${recordingId}`
      ),
    enabled: !!recordingId && enabled,
  })
}

export function useDocument(id: string): UseQueryResult<Document> {
  return useQuery({
    queryKey: ["documents", id],
    queryFn: () => apiClient.get<Document>(`/api/documents/${id}`),
    enabled: !!id,
  })
}

export function useGeneratePrd(
  recordingId: string
): UseMutationResult<Document, Error, void> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiClient.post<Document>(
        `/api/recordings/${recordingId}/generate-prd`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      toast.success("PRD generated successfully")
    },
    onError: (error: Error) => {
      toast.error(`Failed to generate PRD: ${error.message}`)
    },
  })
}

export function useGenerateDiagram(
  recordingId: string
): UseMutationResult<Document, Error, void> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiClient.post<Document>(
        `/api/recordings/${recordingId}/generate-diagram`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      toast.success("Diagram generated successfully")
    },
    onError: (error) => {
      toast.error(`Failed to generate diagram: ${error.message}`)
    },
  })
}

