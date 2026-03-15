"use client"

import { useEffect, useRef, useState } from "react"
import { Upload, FileText, X, Loader2, Mic, Play } from "lucide-react"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn, formatDuration } from "@/lib/utils"
import { useProjects } from "@/hooks/use-projects"

export interface AudioPayload {
  file: Blob | File
  recordingId: string
  title: string
  durationMs: number
  source: "record" | "upload"
}

interface RecordingPrepareDialogProps {
  payload: AudioPayload | null
  onClose: () => void
}

interface AttachedDoc {
  id: string
  file: File
}

const ACCEPTED_DOCS = ".pdf,.pptx,.ppt"

export function RecordingPrepareDialog({ payload, onClose }: RecordingPrepareDialogProps) {
  const queryClient = useQueryClient()
  const docInputRef = useRef<HTMLInputElement>(null)
  // Track when the OS file-picker is open so we don't accidentally close the dialog
  // when it temporarily steals browser focus.
  const isPickingFile = useRef(false)
  const [title, setTitle] = useState(payload?.title ?? "")
  const [selectedProjectId, setSelectedProjectId] = useState<string>("none")
  const [docs, setDocs] = useState<AttachedDoc[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Reset the flag when focus returns to the window after the OS file picker closes.
  useEffect(() => {
    const handleFocus = () => {
      // Small delay so the flag is still set during the base-ui close check that
      // fires synchronously when focus returns.
      setTimeout(() => { isPickingFile.current = false }, 200)
    }
    window.addEventListener("focus", handleFocus)
    return () => window.removeEventListener("focus", handleFocus)
  }, [])

  const { data: projects = [] } = useProjects()

  // Sync state when a new payload arrives
  const currentPayloadId = payload?.recordingId
  const [lastPayloadId, setLastPayloadId] = useState<string | undefined>()
  if (currentPayloadId !== lastPayloadId) {
    setLastPayloadId(currentPayloadId)
    setTitle(payload?.title ?? "")
    setSelectedProjectId("none")
    setDocs([])
  }

  function openFilePicker() {
    isPickingFile.current = true
    docInputRef.current?.click()
  }

  function addDocs(files: FileList | null) {
    isPickingFile.current = false
    if (!files) return
    const newDocs: AttachedDoc[] = Array.from(files).map((f) => ({
      id: crypto.randomUUID(),
      file: f,
    }))
    setDocs((prev) => [...prev, ...newDocs])
    if (docInputRef.current) docInputRef.current.value = ""
  }

  function removeDoc(id: string) {
    setDocs((prev) => prev.filter((d) => d.id !== id))
  }

  async function handleProcess() {
    if (!payload) return
    setIsSubmitting(true)

    try {
      // 1. Upload the audio recording
      const audioForm = new FormData()
      const filename = `${payload.recordingId}.webm`
      audioForm.append("file", payload.file, filename)
      audioForm.append("recordingId", payload.recordingId)
      audioForm.append("title", title.trim() || payload.title)
      audioForm.append("durationMs", String(payload.durationMs))
      if (selectedProjectId && selectedProjectId !== "none") {
        audioForm.append("projectId", selectedProjectId)
      }

      const audioRes = await fetch("/api/recordings", {
        method: "POST",
        body: audioForm,
      })

      if (!audioRes.ok) throw new Error("Audio upload failed")

      const recording = await audioRes.json()
      const recordingId: string = recording.id

      // 2. Upload any attached documents — await all so they land before extraction starts
      if (docs.length > 0) {
        await Promise.allSettled(
          docs.map(({ file }) => {
            const docForm = new FormData()
            docForm.append("file", file, file.name)
            return fetch(`/api/recordings/${recordingId}/documents`, {
              method: "POST",
              body: docForm,
            })
          })
        )
      }

      queryClient.invalidateQueries({ queryKey: ["recordings"] })

      const docNote = docs.length > 0
        ? ` with ${docs.length} document${docs.length > 1 ? "s" : ""}`
        : ""
      toast.success("Processing started", {
        description: `"${title.trim() || payload.title}" is being transcribed${docNote}.`,
      })

      onClose()
    } catch {
      toast.error("Failed to start processing", {
        description: "Please try again.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog
      open={payload !== null}
      onOpenChange={(v) => {
        // Don't close if we're waiting on the OS file picker or mid-submit
        if (!v && !isSubmitting && !isPickingFile.current) onClose()
      }}
    >
      <DialogContent className="max-w-lg overflow-y-auto max-h-[90dvh]" showCloseButton={!isSubmitting}>
        <DialogHeader>
          <DialogTitle className="font-heading text-lg">
            {payload?.source === "record" ? "Save Recording" : "Upload Audio"}
          </DialogTitle>
          <DialogDescription>
            {payload?.source === "record"
              ? "Review your recording, optionally attach slides, then start processing."
              : "Optionally attach presentation slides before processing begins."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Audio preview row */}
          <div className="flex items-center gap-3 rounded-xl border bg-muted/30 px-4 py-3">
            {payload?.source === "record" ? (
              <Mic className="h-5 w-5 shrink-0 text-primary" />
            ) : (
              <Play className="h-5 w-5 shrink-0 text-primary" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{title || payload?.title}</p>
              {payload && payload.durationMs > 0 && (
                <p className="text-xs text-muted-foreground">{formatDuration(payload.durationMs)}</p>
              )}
            </div>
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <Label htmlFor="rec-title">Title</Label>
            <Input
              id="rec-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Recording title"
            />
          </div>

          {/* Project */}
          <div className="space-y-1.5">
            <Label>
              Project{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger>
                <SelectValue placeholder="No project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No project</SelectItem>
                {(projects as { id: string; name: string }[]).map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Document upload */}
          <div className="space-y-2">
            <Label>
              Slides / Documents{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Attach a PDF or PPTX and the AI will reference specific slides when extracting outcomes.
            </p>

            {docs.length > 0 && (
              <ul className="space-y-1.5">
                {docs.map((d) => (
                  <li
                    key={d.id}
                    className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2"
                  >
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="flex-1 min-w-0 truncate text-sm">{d.file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeDoc(d.id)}
                      className="shrink-0 rounded p-0.5 hover:bg-muted transition-colors"
                      aria-label={`Remove ${d.file.name}`}
                    >
                      <X className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <input
              ref={docInputRef}
              type="file"
              accept={ACCEPTED_DOCS}
              multiple
              className="hidden"
              aria-hidden="true"
              onChange={(e) => addDocs(e.target.files)}
            />
            <button
              type="button"
              onClick={openFilePicker}
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-3 text-sm text-muted-foreground transition-colors",
                "hover:border-primary/40 hover:text-foreground hover:bg-muted/20"
              )}
            >
              <Upload className="h-4 w-4" />
              {docs.length === 0 ? "Attach PDF or PPTX" : "Attach another file"}
            </button>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 pt-1">
            <Button
              className="flex-1 gap-2"
              onClick={handleProcess}
              disabled={isSubmitting}
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isSubmitting ? "Starting…" : "Start Processing"}
            </Button>
            <Button
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
