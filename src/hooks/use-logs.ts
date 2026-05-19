"use client"

import {
  useQuery,
  type UseQueryResult,
} from "@tanstack/react-query"

import { apiClient } from "@/lib/api/client"
import type { LogEvent, LogFilters } from "@/types/log"

function buildQuery(filters: LogFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && String(value).trim()) {
      params.set(key, String(value))
    }
  }
  const query = params.toString()
  return query ? `?${query}` : ""
}

export function useLogs(filters: LogFilters = {}): UseQueryResult<LogEvent[]> {
  return useQuery({
    queryKey: ["logs", filters],
    queryFn: () => apiClient.get<LogEvent[]>(`/api/logs${buildQuery(filters)}`),
    refetchInterval: 3000,
  })
}
