"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toast } from "sonner"

import { apiClient } from "@/lib/api/client"

export interface Attachment {
  id: string
  recording_id: string
  filename: string
  file_type: string
  file_size: number
  extraction_error: string | null
  created_at: string
}

export function useAttachments(recordingId: string, enabled = true) {
  return useQuery<Attachment[]>({
    queryKey: ["attachments", recordingId],
    queryFn: () =>
      apiClient.get<Attachment[]>(`/api/recordings/${recordingId}/attachments`),
    enabled: !!recordingId && enabled,
  })
}

export function useUploadAttachment(recordingId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      return apiClient.post<Attachment>(
        `/api/recordings/${recordingId}/attachments`,
        formData
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments", recordingId] })
    },
    onError: (error: Error) => {
      toast.error("Upload failed", { description: error.message })
    },
  })
}

export function useDeleteAttachment(recordingId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (attachmentId: string) =>
      apiClient.delete<void>(
        `/api/recordings/${recordingId}/attachments/${attachmentId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments", recordingId] })
      toast.success("Document removed")
    },
    onError: (error: Error) => {
      toast.error("Delete failed", { description: error.message })
    },
  })
}
