"use client"

import { useEffect, useRef, useState, useDeferredValue } from "react"
import { toast } from "sonner"
import { Search } from "lucide-react"

import { Input } from "@/components/ui/input"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table"
import { RecordingRow } from "@/components/recording/recording-row"
import {
  useRecordings,
  useRecordingStatus,
  useAssignProject,
} from "@/hooks/use-recordings"
import type { Recording, RecordingStatus } from "@/types/recording"

const TABS = [
  { value: "all", label: "All" },
  { value: "unassigned", label: "Unassigned" },
  { value: "processing", label: "Processing" },
  { value: "ready", label: "Ready" },
] as const

/**
 * Polls status for a single processing recording.
 * Shows toast on completion or error.
 */
function ProcessingPoller({ recording }: { recording: Recording }) {
  const prevStatusRef = useRef(recording.status)

  const { data } = useRecordingStatus(
    recording.id,
    recording.status === "processing"
  )

  useEffect(() => {
    if (!data) return

    const prevStatus = prevStatusRef.current
    if (prevStatus === "processing" && data.status === "ready") {
      toast.success("Transcription complete!", {
        description: `"${recording.title}" is ready for review.`,
      })
    } else if (prevStatus === "processing" && data.status === "error") {
      toast.error("Transcription failed", {
        description: `"${recording.title}" encountered an error.`,
      })
    }

    prevStatusRef.current = data.status
  }, [data, recording.title])

  return null
}

export function RecordingHub() {
  const { data: allRecordings = [], isLoading } = useRecordings()
  const assignProject = useAssignProject()

  // Search and project filter state
  const [query, setQuery] = useState("")
  const deferredQuery = useDeferredValue(query)
  const [projectFilter, setProjectFilter] = useState<string>("all")

  const handleAssignProject = (recordingId: string, projectId: string) => {
    assignProject.mutate({ recordingId, projectId })
  }

  // Extract unique project IDs for the dropdown
  const projects = [
    ...new Set(
      allRecordings.filter((r) => r.projectId).map((r) => r.projectId!)
    ),
  ]

  // Apply search filter
  const searchFiltered = deferredQuery
    ? allRecordings.filter((r) =>
        r.title.toLowerCase().includes(deferredQuery.toLowerCase())
      )
    : allRecordings

  // Apply project filter
  const filtered =
    projectFilter === "all"
      ? searchFiltered
      : searchFiltered.filter((r) => r.projectId === projectFilter)

  // Count recordings by status (from filtered set)
  const counts = {
    all: filtered.length,
    unassigned: filtered.filter((r) => r.status === "unassigned").length,
    processing: filtered.filter((r) => r.status === "processing").length,
    ready: filtered.filter((r) => r.status === "ready").length,
  }

  // Processing recordings need status polling (from all, not filtered)
  const processingRecordings = allRecordings.filter(
    (r) => r.status === "processing"
  )

  const filterRecordings = (tab: string): Recording[] => {
    if (tab === "all") return filtered
    return filtered.filter((r) => r.status === tab)
  }

  const renderTable = (recordings: Recording[]) => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Duration</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Project</TableHead>
          <TableHead>Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {recordings.length === 0 ? (
          <TableRow>
            <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
              No recordings found
            </TableCell>
          </TableRow>
        ) : (
          recordings.map((recording) => (
            <RecordingRow
              key={recording.id}
              recording={recording}
              onAssignProject={handleAssignProject}
            />
          ))
        )}
      </TableBody>
    </Table>
  )

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Status pollers for processing recordings */}
      {processingRecordings.map((r) => (
        <ProcessingPoller key={r.id} recording={r} />
      ))}

      {/* Search and project filter controls */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search recordings..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        {projects.length > 0 && (
          <Select value={projectFilter} onValueChange={setProjectFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              {projects.map((pid) => (
                <SelectItem key={pid} value={pid}>
                  {pid}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
              <span className="ml-1 text-xs text-muted-foreground">
                ({counts[tab.value as keyof typeof counts]})
              </span>
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            {renderTable(filterRecordings(tab.value))}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
