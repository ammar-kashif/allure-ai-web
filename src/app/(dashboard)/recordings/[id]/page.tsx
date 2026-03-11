"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeft, Loader2 } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusBadge } from "@/components/recording/status-badge"
import { TranscriptView } from "@/components/transcript/transcript-view"
import { useRecording, useRecordingStatus, useTranscript } from "@/hooks/use-recordings"
import { formatDuration, formatTimestamp } from "@/lib/utils"
import { cn } from "@/lib/utils"

export default function RecordingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const { data: recording, isLoading, error } = useRecording(id)

  const isProcessing = recording?.status === "processing"
  const isReady = recording?.status === "ready"

  // Poll status while processing
  useRecordingStatus(id, isProcessing)

  // Fetch transcript only when ready
  const {
    data: transcript,
    isLoading: isTranscriptLoading,
  } = useTranscript(id, isReady)

  if (isLoading) {
    return <RecordingDetailSkeleton />
  }

  if (error || !recording) {
    return (
      <div className="space-y-6">
        <BackButton />
        <div className="py-12 text-center">
          <h2 className="text-xl font-semibold">Recording not found</h2>
          <p className="mt-2 text-muted-foreground">
            The recording you are looking for does not exist or has been removed.
          </p>
          <Link
            href="/recordings"
            className={cn(buttonVariants({ variant: "outline" }), "mt-4 inline-flex")}
          >
            Back to Recordings
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <BackButton />

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight">
            {recording.title}
          </h2>
          <StatusBadge status={recording.status} />
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{formatTimestamp(recording.createdAt)}</span>
          <span>{formatDuration(recording.durationMs)}</span>
          {recording.projectId && (
            <span>Project assigned</span>
          )}
        </div>
      </div>

      {/* Content based on status */}
      {recording.status === "unassigned" && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-muted-foreground">
            Assign to a project to begin transcription
          </p>
          <Link
            href="/recordings"
            className={cn(buttonVariants({ variant: "outline" }), "mt-4 inline-flex")}
          >
            Go to Recording Hub
          </Link>
        </div>
      )}

      {recording.status === "processing" && (
        <div className="flex flex-col items-center gap-3 py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-muted-foreground">Transcribing...</p>
        </div>
      )}

      {recording.status === "error" && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="font-medium text-destructive">Transcription Error</p>
          <p className="mt-1 text-sm text-destructive/80">
            {recording.errorMessage || "An unknown error occurred during transcription."}
          </p>
        </div>
      )}

      {recording.status === "ready" && (
        <>
          {isTranscriptLoading ? (
            <TranscriptSkeleton />
          ) : transcript ? (
            <TranscriptView transcript={transcript} />
          ) : (
            <div className="py-12 text-center text-muted-foreground">
              No transcript content available
            </div>
          )}
        </>
      )}
    </div>
  )
}

function BackButton() {
  return (
    <Link
      href="/recordings"
      className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-2")}
    >
      <ArrowLeft className="mr-1 h-4 w-4" />
      Recordings
    </Link>
  )
}

function RecordingDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-24" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <TranscriptSkeleton />
    </div>
  )
}

function TranscriptSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="space-y-1">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-16 w-[70%]" />
        </div>
      ))}
    </div>
  )
}
