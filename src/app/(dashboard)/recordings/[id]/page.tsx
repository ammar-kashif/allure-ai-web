"use client"

import { use, useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft, Loader2, MoreVertical, Pencil, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { StatusBadge } from "@/components/recording/status-badge"
import { TranscriptView } from "@/components/transcript/transcript-view"
import { AudioPlayer, type AudioPlayerHandle } from "@/components/transcript/audio-player"
import { SpeakerStatsPanel } from "@/components/transcript/speaker-stats-panel"
import { OutcomesTab } from "@/components/outcome/outcomes-tab"
import { DecisionChartTab } from "@/components/chart/decision-chart-tab"
import { DocumentTab } from "@/components/document/document-tab"
import { CommentThread } from "@/components/comment/comment-thread"
import {
  useRecording,
  useRecordingStatus,
  useTranscript,
  useRenameRecording,
  useDeleteRecording,
  useRenameSpeaker,
  useUpdateSpeakerRole,
} from "@/hooks/use-recordings"
import { useProjects } from "@/hooks/use-projects"
import { useEvidenceHighlight, type TabId } from "@/stores/evidence-highlight"
import { formatDuration, formatTimestamp, cn } from "@/lib/utils"

export default function RecordingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const router = useRouter()
  const { data: recording, isLoading, error } = useRecording(id)
  const { data: projectList = [] } = useProjects()

  const isProcessing = recording?.status === "processing"
  const isReady = recording?.status === "ready"

  useRecordingStatus(id, isProcessing)

  const { data: transcript, isLoading: isTranscriptLoading } = useTranscript(
    id,
    isReady
  )

  const activeTab = useEvidenceHighlight((s) => s.activeTab)
  const setActiveTab = useEvidenceHighlight((s) => s.setActiveTab)
  const setHighlight = useEvidenceHighlight((s) => s.setHighlight)

  const searchParams = useSearchParams()
  useEffect(() => {
    const h = searchParams.get("highlight")
    if (h !== null && isReady) {
      const idx = parseInt(h, 10)
      if (!isNaN(idx)) setHighlight(idx)
    }
  }, [searchParams, isReady, setHighlight])

  // Rename recording
  const renameMutation = useRenameRecording()
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const titleInputRef = useRef<HTMLInputElement>(null)

  const startEditing = useCallback(() => {
    if (recording) {
      setEditTitle(recording.title)
      setIsEditing(true)
    }
  }, [recording])

  useEffect(() => {
    if (isEditing && titleInputRef.current) {
      titleInputRef.current.focus()
      titleInputRef.current.select()
    }
  }, [isEditing])

  const saveTitle = useCallback(() => {
    const trimmed = editTitle.trim()
    if (trimmed && trimmed !== recording?.title) {
      renameMutation.mutate({ recordingId: id, title: trimmed })
    }
    setIsEditing(false)
  }, [editTitle, recording?.title, id, renameMutation])

  const cancelEditing = useCallback(() => setIsEditing(false), [])

  // Delete
  const deleteMutation = useDeleteRecording()
  const handleDelete = useCallback(() => {
    if (
      !window.confirm(
        "Are you sure you want to delete this recording? This cannot be undone."
      )
    ) {
      return
    }
    deleteMutation.mutate(id, {
      onSuccess: () => router.push("/recordings"),
    })
  }, [id, deleteMutation, router])

  // Audio playback
  const audioPlayerRef = useRef<AudioPlayerHandle>(null)
  const [playingIndex, setPlayingIndex] = useState<number | null>(null)
  const audioUrl = `/api/recordings/${id}/audio`

  const handleSeek = useCallback((seconds: number) => {
    audioPlayerRef.current?.seekTo(seconds)
  }, [])

  // Speaker rename
  const renameSpeakerMutation = useRenameSpeaker()
  const handleRenameSpeaker = useCallback(
    (oldLabel: string, newLabel: string) => {
      renameSpeakerMutation.mutate({ recordingId: id, renames: { [oldLabel]: newLabel } })
    },
    [id, renameSpeakerMutation]
  )

  // Speaker role update
  const updateRoleMutation = useUpdateSpeakerRole()
  const handleRoleChange = useCallback(
    (label: string, newRole: string) => {
      updateRoleMutation.mutate({ recordingId: id, roles: { [label]: newRole } })
    },
    [id, updateRoleMutation]
  )

  // Build a label → role lookup map for use in utterance bubbles
  const speakerRoles: Record<string, string> = {}
  if (transcript?.speakers) {
    for (const spk of transcript.speakers) {
      if (spk.role) speakerRoles[spk.label] = spk.role
    }
  }

  if (isLoading) return <RecordingDetailSkeleton />

  if (error || !recording) {
    return (
      <div className="space-y-6">
        <BackLink />
        <div className="py-12 text-center">
          <h2 className="text-xl font-semibold">Recording not found</h2>
          <p className="mt-2 text-muted-foreground">
            The recording you are looking for does not exist or has been removed.
          </p>
          <Link href="/recordings" className="mt-4 inline-flex underline text-sm text-muted-foreground">
            Back to Recordings
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <BackLink />

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          {isEditing ? (
            <input
              ref={titleInputRef}
              className="text-[1.75rem] font-heading font-bold tracking-[-0.02em] bg-transparent border-b border-primary outline-none"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={saveTitle}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveTitle()
                if (e.key === "Escape") cancelEditing()
              }}
            />
          ) : (
            <h2
              className="text-[1.75rem] font-heading font-bold tracking-[-0.02em] cursor-pointer hover:opacity-70 transition-opacity"
              onClick={startEditing}
              title="Click to rename"
            >
              {recording.title}
            </h2>
          )}
          <StatusBadge status={recording.status} />

          <DropdownMenu>
            <DropdownMenuTrigger>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={startEditing}>
                <Pencil className="mr-2 h-4 w-4" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center gap-4 text-[0.8125rem] text-muted-foreground">
          <span>{formatTimestamp(recording.createdAt)}</span>
          <span>{formatDuration(recording.durationMs)}</span>
          {recording.projectId && (
            <span>
              {projectList.find((p) => p.id === recording.projectId)?.name ||
                "Project assigned"}
            </span>
          )}
        </div>
      </div>

      {/* Status-dependent content */}
      {recording.status === "unassigned" && (
        <div className="rounded-xl border border-dashed p-8 text-center shadow-[var(--shadow-xs)]">
          <p className="text-muted-foreground">
            Assign to a project to begin transcription
          </p>
          <Link
            href="/recordings"
            className="mt-4 inline-flex underline text-sm text-muted-foreground"
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
            {recording.errorMessage ||
              "An unknown error occurred during transcription."}
          </p>
        </div>
      )}

      {recording.status === "ready" && (
        <Tabs
          value={activeTab}
          onValueChange={(val: string) => setActiveTab(val as TabId)}
        >
          <TabsList>
            <TabsTrigger value="info">Info</TabsTrigger>
            <TabsTrigger value="transcript">Transcript</TabsTrigger>
            <TabsTrigger value="outcomes">Outcomes</TabsTrigger>
            <TabsTrigger value="chart">Decision Chart</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
          </TabsList>

          {/* Info tab */}
          <TabsContent value="info">
            <div className="space-y-4 pt-4">
              <div className="rounded-xl bg-card p-5 shadow-[var(--shadow-card)] space-y-3">
                <h3 className="font-heading font-semibold tracking-[-0.01em]">
                  Recording Info
                </h3>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-[0.9375rem]">
                  <dt className="text-muted-foreground">Title</dt>
                  <dd>{recording.title}</dd>
                  <dt className="text-muted-foreground">Duration</dt>
                  <dd>{formatDuration(recording.durationMs)}</dd>
                  <dt className="text-muted-foreground">Created</dt>
                  <dd>{formatTimestamp(recording.createdAt)}</dd>
                  <dt className="text-muted-foreground">Status</dt>
                  <dd className="capitalize">{recording.status}</dd>
                  {recording.projectId && (
                    <>
                      <dt className="text-muted-foreground">Project</dt>
                      <dd>
                        {projectList.find((p) => p.id === recording.projectId)
                          ?.name || recording.projectId}
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            </div>
          </TabsContent>

          {/* Transcript tab */}
          <TabsContent value="transcript">
            <div className="pt-4 space-y-4">
              {isTranscriptLoading ? (
                <TranscriptSkeleton />
              ) : transcript ? (
                <>
                  {transcript.speakers && transcript.speakers.length > 0 && (
                    <SpeakerStatsPanel
                      speakers={transcript.speakers}
                      onRename={handleRenameSpeaker}
                      onRoleChange={handleRoleChange}
                    />
                  )}

                  <AudioPlayer
                    ref={audioPlayerRef}
                    audioUrl={audioUrl}
                    utterances={transcript.utterances}
                    onCurrentUtteranceChange={setPlayingIndex}
                  />

                  <TranscriptView
                    transcript={transcript}
                    playingUtteranceIndex={playingIndex}
                    onSeek={handleSeek}
                    onRenameSpeaker={handleRenameSpeaker}
                    speakerRoles={speakerRoles}
                  />
                </>
              ) : (
                <div className="py-12 text-center text-muted-foreground">
                  No transcript content available
                </div>
              )}
            </div>
          </TabsContent>

          {/* Outcomes tab */}
          <TabsContent value="outcomes">
            <div className="pt-4">
              <OutcomesTab recordingId={id} projectId={recording.projectId ?? undefined} />
            </div>
          </TabsContent>

          {/* Decision Chart tab */}
          <TabsContent value="chart">
            <div className="pt-4">
              <DecisionChartTab recordingId={id} />
            </div>
          </TabsContent>

          {/* Documents tab */}
          <TabsContent value="documents">
            <div className="pt-4 space-y-6">
              <DocumentTab
                recordingId={id}
                transcriptUtterances={transcript?.utterances.map((u) => ({
                  speaker: u.speaker,
                  text: u.text,
                  startTime: u.startTime,
                }))}
              />
              <CommentThread entityType="recording" entityId={id} className="pt-4 border-t" />
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function BackLink() {
  return (
    <Link
      href="/recordings"
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors -ml-1"
    >
      <ArrowLeft className="h-4 w-4" />
      Recordings
    </Link>
  )
}

function RecordingDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-20" />
      <div className="space-y-2">
        <Skeleton className="h-9 w-64" />
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
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-3 w-20" />
          <Skeleton
            className={cn("h-14", i % 2 === 0 ? "w-[65%]" : "w-[80%]")}
          />
        </div>
      ))}
    </div>
  )
}
