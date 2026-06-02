"use client"

import { useRecordings } from "@/hooks/use-recordings"
import { useQueries, useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api/client"
import type { OutcomesResponse, Task } from "@/types/outcome"
import type { Recording } from "@/types/recording"
import type { Document } from "@/lib/db/documents"

interface DashboardStats {
  totalRecordings: number
  outcomesExtracted: number
  tasksCreated: number
  documentsGenerated: number
  isLoading: boolean
  recordings: Recording[]
  allOutcomes: Array<
    OutcomesResponse["outcomes"][number] & { recordingId: string }
  >
}

export function useDashboardStats(): DashboardStats {
  const { data: recordings = [], isLoading: recordingsLoading } =
    useRecordings()

  // Fetch outcomes for all "ready" recordings in parallel
  const readyRecordings = recordings.filter((r) => r.status === "ready")

  const outcomeQueries = useQueries({
    queries: readyRecordings.map((r) => ({
      queryKey: ["outcomes", r.id],
      queryFn: () =>
        apiClient.get<OutcomesResponse>(
          `/api/recordings/${r.id}/outcomes`
        ),
      staleTime: 30_000,
    })),
  })

  // Fetch actual task count from database
  const { data: tasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ["tasks", "all"],
    queryFn: () => apiClient.get<Task[]>("/api/tasks"),
    staleTime: 30_000,
  })

  // Fetch document count
  const { data: documents = [], isLoading: documentsLoading } = useQuery({
    queryKey: ["documents", "all"],
    queryFn: () => apiClient.get<Document[]>("/api/documents"),
    staleTime: 30_000,
  })

  const outcomesLoading = outcomeQueries.some((q) => q.isLoading) || tasksLoading

  // Flatten all outcomes with their recording IDs
  const allOutcomes = outcomeQueries.flatMap((q, i) => {
    const recordingId = readyRecordings[i]?.id
    if (!q.data?.outcomes || !recordingId) return []
    return q.data.outcomes.map((o) => ({ ...o, recordingId }))
  })

  const outcomesExtracted = allOutcomes.length
  const tasksCreated = tasks.length
  const documentsGenerated = documents.length

  return {
    totalRecordings: recordings.length,
    outcomesExtracted,
    tasksCreated,
    documentsGenerated,
    isLoading: recordingsLoading || outcomesLoading || documentsLoading,
    recordings,
    allOutcomes,
  }
}

