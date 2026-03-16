"use client"

import { use, useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import {
  ArrowLeft,
  FileText,
  Loader2,
  MoreVertical,
  Pencil,
  Share2,
  Trash2,
} from "lucide-react"

import { Button, buttonVariants } from "@/components/ui/button"
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
import { OutcomesTab } from "@/components/outcome/outcomes-tab"
import {
  useRecording,
  useRecordingStatus,
  useTranscript,
  useRenameRecording,
  useDeleteRecording,
} from "@/hooks/use-recordings"
import {
  useGeneratePrd,
  useGenerateDiagram,
  useDocumentsByRecording,
} from "@/hooks/use-documents"
import { MermaidDiagram } from "@/components/document/mermaid-diagram"
import { PrdContent } from "@/components/document/prd-content"
import { useProjects } from "@/hooks/use-projects"
import { useEvidenceHighlight } from "@/stores/evidence-highlight"
import { formatDuration, formatTimestamp } from "@/lib/utils"
import { cn } from "@/lib/utils"

import type { TabId } from "@/stores/evidence-highlight"

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
  const setHighlight = useEvidenceHighlight((s) => s.setHighlight)

  // Apply highlight from URL search param (e.g. ?highlight=2)
  const searchParams = useSearchParams()
  useEffect(() => {
    const h = searchParams.get("highlight")
    if (h !== null && isReady) {
      const idx = parseInt(h, 10)
      if (!isNaN(idx)) setHighlight(idx)
    }
  }, [searchParams, isReady, setHighlight])

  // Rename
  const renameMutation = useRenameRecording()
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const startEditing = useCallback(() => {
    if (recording) {
      setEditTitle(recording.title)
      setIsEditing(true)
    }
  }, [recording])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const saveTitle = useCallback(() => {
    const trimmed = editTitle.trim()
    if (trimmed && trimmed !== recording?.title) {
      renameMutation.mutate({ recordingId: id, title: trimmed })
    }
    setIsEditing(false)
  }, [editTitle, recording?.title, id, renameMutation])

  const cancelEditing = useCallback(() => {
    setIsEditing(false)
  }, [])

  // Document generation
  const generatePrd = useGeneratePrd(id)
  const generateDiagram = useGenerateDiagram(id)

  // Fetch documents for this recording
  const { data: recordingDocs = [] } = useDocumentsByRecording(id, isReady)
  const latestPrd = recordingDocs.find((d) => d.type === "prd")
  const latestDiagram = recordingDocs.find(
    (d) => d.type === "user_flow" || d.type === "erd"
  )

  // Delete
  const deleteMutation = useDeleteRecording()

  const handleDelete = useCallback(() => {
    if (!window.confirm("Are you sure you want to delete this recording? This cannot be undone.")) {
      return
    }
    deleteMutation.mutate(id, {
      onSuccess: () => router.push("/recordings"),
    })
  }, [id, deleteMutation, router])

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
    <div className="space-y-8">
      <BackButton />

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          {isEditing ? (
            <input
              ref={inputRef}
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
              className="text-[1.75rem] font-heading font-bold tracking-[-0.02em] cursor-pointer hover:text-muted-foreground transition-colors duration-[var(--duration-fast)]"
              onClick={startEditing}
              title="Click to rename"
            >
              {recording.title}
            </h2>
          )}
          <StatusBadge status={recording.status} />

          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="ghost" size="icon" className="h-8 w-8" />}
            >
              <MoreVertical className="h-4 w-4" />
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
            <span>{projectList.find((p) => p.id === recording.projectId)?.name || "Project assigned"}</span>
          )}
        </div>
      </div>

      {/* Content based on status */}
      {recording.status === "unassigned" && (
        <div className="rounded-xl border border-dashed p-8 text-center shadow-[var(--shadow-xs)]">
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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={generatePrd.isPending}
            onClick={() => {
              generatePrd.mutate(undefined, {
                onSuccess: () => setActiveTab("prd"),
              })
            }}
          >
            {generatePrd.isPending ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <FileText className="mr-1.5 h-4 w-4" />
            )}
            {generatePrd.isPending ? "Generating..." : latestPrd ? "Regenerate PRD" : "Generate PRD"}
          </Button>

          <Button
            variant="outline"
            size="sm"
            disabled={generateDiagram.isPending}
            onClick={() => {
              generateDiagram.mutate(undefined, {
                onSuccess: () => setActiveTab("diagram"),
              })
            }}
          >
            {generateDiagram.isPending ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <Share2 className="mr-1.5 h-4 w-4" />
            )}
            {generateDiagram.isPending ? "Generating..." : latestDiagram ? "Regenerate Diagram" : "Generate Diagram"}
          </Button>
        </div>

        <Tabs
          value={activeTab}
          onValueChange={(value: string) => {
            setActiveTab(value as TabId)
          }}
        >
          <TabsList>
            <TabsTrigger value="info">Info</TabsTrigger>
            <TabsTrigger value="transcript">Transcript</TabsTrigger>
            <TabsTrigger value="outcomes">Outcomes</TabsTrigger>
            {latestPrd && <TabsTrigger value="prd">PRD</TabsTrigger>}
            {latestDiagram && <TabsTrigger value="diagram">Diagram</TabsTrigger>}
          </TabsList>

          <TabsContent value="info">
            <div className="space-y-4 pt-4">
              <div className="rounded-xl bg-card p-5 shadow-[var(--shadow-card)] space-y-3">
                <h3 className="font-heading font-semibold tracking-[-0.01em]">Recording Info</h3>
                <div className="grid grid-cols-2 gap-2 text-[0.9375rem]">
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
                      <span>{projectList.find((p) => p.id === recording.projectId)?.name || recording.projectId}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="transcript">
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

          <TabsContent value="outcomes">
            <div className="pt-4">
              <OutcomesTab recordingId={id} />
            </div>
          </TabsContent>

          {latestPrd && (
            <TabsContent value="prd">
              <div className="pt-4">
                <PrdContent content={latestPrd.content} />
              </div>
            </TabsContent>
          )}

          {latestDiagram && (
            <TabsContent value="diagram">
              <div className="pt-4">
                <div className="rounded-xl bg-card p-6 shadow-[var(--shadow-card)]">
                  <MermaidDiagram code={latestDiagram.content} />
                </div>
              </div>
            </TabsContent>
          )}
        </Tabs>
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

