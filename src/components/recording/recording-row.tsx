"use client"

import { useRouter } from "next/navigation"

import { TableRow, TableCell } from "@/components/ui/table"
import { StatusBadge } from "@/components/recording/status-badge"
import { ProjectAssignment } from "@/components/recording/project-assignment"
import { formatDuration, formatTimestamp } from "@/lib/utils"
import type { Recording } from "@/types/recording"

interface RecordingRowProps {
  recording: Recording
  onAssignProject: (recordingId: string, projectId: string) => void
}

export function RecordingRow({ recording, onAssignProject }: RecordingRowProps) {
  const router = useRouter()

  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => router.push(`/recordings/${recording.id}`)}
    >
      <TableCell className="font-medium">{recording.title}</TableCell>
      <TableCell className="font-numeric">{formatDuration(recording.durationMs)}</TableCell>
      <TableCell>
        <StatusBadge status={recording.status} />
      </TableCell>
      <TableCell>
        <ProjectAssignment
          currentProjectId={recording.projectId}
          onAssign={(projectId) => onAssignProject(recording.id, projectId)}
        />
      </TableCell>
      <TableCell className="text-muted-foreground font-numeric">
        {formatTimestamp(recording.createdAt)}
      </TableCell>
    </TableRow>
  )
}
