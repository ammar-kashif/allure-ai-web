"use client"

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import type { Project } from "@/types/recording"

export function useProjects(): UseQueryResult<Project[]> {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.get<Project[]>("/api/projects"),
  })
}

export function useCreateProject(): UseMutationResult<
  Project,
  Error,
  { name: string }
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name }: { name: string }) =>
      apiClient.post<Project>("/api/projects", { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
    },
  })
}

