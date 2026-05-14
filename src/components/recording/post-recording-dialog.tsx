"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertCircle, Check, Loader2 } from "lucide-react"
import { toast } from "sonner"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FileDropZone } from "@/components/recording/file-drop-zone"
import { useRecordingStore } from "@/stores/recording-store"
import {
  useRecordingStatus,
  useRenameRecording,
  useAssignProject,
} from "@/hooks/use-recordings"
import { useProjects } from "@/hooks/use-projects"

const UNASSIGNED_VALUE = "__unassigned__"

export function PostRecordingDialog() {
  const showDialog = useRecordingStore((s) => s.showPostRecordingDialog)
  const pendingRecording = useRecordingStore((s) => s.pendingRecording)
  const closeDialog = useRecordingStore((s) => s.closePostRecordingDialog)

  const [title, setTitle] = useState("")
  const [projectId, setProjectId] = useState(UNASSIGNED_VALUE)
  const [files, setFiles] = useState<File[]>([])
  const [isSaving, setIsSaving] = useState(false)

  const { data: projects } = useProjects()
  const renameRecording = useRenameRecording()
  const assignProject = useAssignProject()

  const recordingId = pendingRecording?.recordingId ?? ""
  const { data: statusData } = useRecordingStatus(recordingId, !!pendingRecording)

  const status = statusData?.status

  // Sync default title when dialog opens
  useEffect(() => {
    if (pendingRecording) {
      setTitle(pendingRecording.defaultTitle)
      setProjectId(UNASSIGNED_VALUE)
      setFiles([])
      setIsSaving(false)
    }
  }, [pendingRecording])

  const showProcessingToast = useCallback(() => {
    if (status && status !== "ready" && status !== "error") {
      toast.info("Transcription in progress", {
        description: "You'll see it in the Recording Hub when ready.",
      })
    }
  }, [status])

  const handleSkip = useCallback(() => {
    showProcessingToast()
    closeDialog()
  }, [showProcessingToast, closeDialog])

  const handleSave = useCallback(async () => {
    if (!pendingRecording) return

    setIsSaving(true)

    try {
      const promises: Promise<unknown>[] = []

      // Rename if title was changed
      if (title && title !== pendingRecording.defaultTitle) {
        promises.push(
          renameRecording.mutateAsync({
            recordingId: pendingRecording.recordingId,
            title,
          })
        )
      }

      // Assign project if selected
      if (projectId !== UNASSIGNED_VALUE) {
        promises.push(
          assignProject.mutateAsync({
            recordingId: pendingRecording.recordingId,
            projectId,
          })
        )
      }

      // Upload reference documents if any
      if (files.length > 0) {
        const formData = new FormData()
        files.forEach((file) => formData.append("files", file))
        promises.push(
          fetch(`/api/recordings/${pendingRecording.recordingId}/documents`, {
            method: "POST",
            body: formData,
          }).then((res) => {
            if (!res.ok) throw new Error("Failed to upload documents")
          })
        )
      }

      await Promise.all(promises)
      showProcessingToast()
      closeDialog()
    } catch {
      toast.error("Failed to save recording details", {
        description: "Please try again.",
      })
    } finally {
      setIsSaving(false)
    }
  }, [
    pendingRecording,
    title,
    projectId,
    files,
    renameRecording,
    assignProject,
    showProcessingToast,
    closeDialog,
  ])

  // Prevent closing via backdrop or escape -- only Save/Skip should close
  const handleOpenChange = useCallback((_open: boolean) => {
    // Intentionally no-op: only Save/Skip handlers can close this dialog
  }, [])

  return (
    <Dialog
      open={showDialog}
      onOpenChange={handleOpenChange}
      disablePointerDismissal
    >
      <DialogContent
        showCloseButton={false}
        className="sm:max-w-lg"
        onKeyDown={(e: React.KeyboardEvent) => {
          // Prevent Escape from closing
          if (e.key === "Escape") {
            e.preventDefault()
            e.stopPropagation()
          }
        }}
      >
        <DialogHeader>
          <DialogTitle className="text-headline">Recording Details</DialogTitle>
          <DialogDescription>
            Name your recording and assign it to a project.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Recording name */}
          <div className="space-y-2">
            <Label htmlFor="recording-name">Recording name</Label>
            <Input
              id="recording-name"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter recording name"
            />
          </div>

          {/* Project selection */}
          <div className="space-y-2">
            <Label>Project</Label>
            <Select
              value={projectId}
              onValueChange={(val) => setProjectId(val as string)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNASSIGNED_VALUE}>Unassigned</SelectItem>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Reference documents */}
          <div className="space-y-2">
            <Label>Reference documents</Label>
            <FileDropZone files={files} onFilesChange={setFiles} />
          </div>
        </div>

        {/* Status line */}
        <div className="flex items-center gap-2 text-sm">
          {status === "processing" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">Transcribing...</span>
            </>
          )}
          {status === "ready" && (
            <>
              <Check className="h-4 w-4 text-foreground" />
              <span className="text-foreground">Transcription complete</span>
            </>
          )}
          {status === "error" && (
            <>
              <AlertCircle className="h-4 w-4 text-destructive" />
              <span className="text-destructive">Transcription failed</span>
            </>
          )}
          {status === "unassigned" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">Processing...</span>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleSkip} disabled={isSaving}>
            Skip
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
