"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toast } from "sonner"

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
    queryFn: async () => {
      const res = await fetch(`/api/recordings/${recordingId}/attachments`)
      if (!res.ok) throw new Error("Failed to fetch attachments")
      return res.json()
    },
    enabled: !!recordingId && enabled,
  })
}

export function useUploadAttachment(recordingId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(`/api/recordings/${recordingId}/attachments`, {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "Upload failed")
        throw new Error(text)
      }

      return res.json() as Promise<Attachment>
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
    mutationFn: async (attachmentId: string) => {
      const res = await fetch(
        `/api/recordings/${recordingId}/attachments/${attachmentId}`,
        { method: "DELETE" }
      )

      if (!res.ok && res.status !== 204) {
        throw new Error("Failed to delete attachment")
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments", recordingId] })
      toast.success("Document removed")
    },
    onError: (error: Error) => {
      toast.error("Delete failed", { description: error.message })
    },
  })
}
