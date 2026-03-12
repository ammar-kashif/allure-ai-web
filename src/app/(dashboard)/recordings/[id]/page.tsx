"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeft, Loader2 } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { StatusBadge } from "@/components/recording/status-badge"
import { TranscriptView } from "@/components/transcript/transcript-view"
import { OutcomesTab } from "@/components/outcome/outcomes-tab"
import { useRecording, useRecordingStatus, useTranscript } from "@/hooks/use-recordings"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import { formatDuration, formatTimestamp } from "@/lib/utils"
import { cn } from "@/lib/utils"

const TAB_MAP = { info: 0, transcript: 1, outcomes: 2 } as const
const TAB_NAMES = ["info", "transcript", "outcomes"] as const

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

  // Evidence highlight store controls active tab
  const activeTab = useEvidenceHighlight((s) => s.activeTab)
  const setActiveTab = useEvidenceHighlight((s) => s.setActiveTab)

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
        <Tabs
          value={TAB_MAP[activeTab]}
          onValueChange={(value: number) => {
            setActiveTab(TAB_NAMES[value])
          }}
        >
          <TabsList>
            <TabsTrigger value={0}>Info</TabsTrigger>
            <TabsTrigger value={1}>Transcript</TabsTrigger>
            <TabsTrigger value={2}>Outcomes</TabsTrigger>
          </TabsList>

          <TabsContent value={0}>
            <div className="space-y-4 pt-4">
              <div className="rounded-lg border p-4 space-y-3">
                <h3 className="font-semibold">Recording Info</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Title</span>
                  <span>{recording.title}</span>
                  <span className="text-muted-foreground">Duration</span>
                  <span>{formatDuration(recording.durationMs)}</span>
                  <span className="text-muted-foreground">Created</span>
                  <span>{formatTimestamp(recording.createdAt)}</span>
                  <span className="text-muted-foreground">Status</span>
                  <span className="capitalize">{recording.status}</span>
                  {recording.projectId && (
                    <>
                      <span className="text-muted-foreground">Project</span>
                      <span>{recording.projectId}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value={1}>
            <div className="pt-4">
              {isTranscriptLoading ? (
                <TranscriptSkeleton />
              ) : transcript ? (
                <TranscriptView transcript={transcript} />
              ) : (
                <div className="py-12 text-center text-muted-foreground">
                  No transcript content available
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value={2}>
            <div className="pt-4">
              <OutcomesTab recordingId={id} />
            </div>
          </TabsContent>
        </Tabs>
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
