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
import type {
  Task,
  TaskFilters,
  CreateTaskInput,
  UpdateTaskInput,
} from "@/types/outcome"

export function useTasks(filters?: TaskFilters): UseQueryResult<Task[]> {
  const params = new URLSearchParams()
  if (filters?.status) params.set("status", filters.status)
  if (filters?.search) params.set("search", filters.search)
  const query = params.toString()
  const path = query ? `/api/tasks?${query}` : "/api/tasks"

  return useQuery({
    queryKey: ["tasks", filters ?? "all"],
    queryFn: () => apiClient.get<Task[]>(path),
  })
}

export function useCreateTask(): UseMutationResult<
  Task,
  Error,
  CreateTaskInput
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTaskInput) =>
      apiClient.post<Task>("/api/tasks", data as unknown as Record<string, unknown>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      toast("Task created")
    },
  })
}

export function useUpdateTask(): UseMutationResult<
  Task,
  Error,
  { id: string } & UpdateTaskInput
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & UpdateTaskInput) =>
      apiClient.patch<Task>(`/api/tasks/${id}`, data as unknown as Record<string, unknown>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useDeleteTask(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`/api/tasks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      toast("Task deleted")
    },
  })
}

