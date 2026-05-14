"use client"

import { useRef, useState } from "react"
import { AlertTriangle, FileText, Loader2, Trash2, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  useAttachments,
  useUploadAttachment,
  useDeleteAttachment,
} from "@/hooks/use-attachments"
import type { Attachment } from "@/hooks/use-attachments"
import { formatFileSize } from "@/lib/utils"

interface AttachedDocumentsCardProps {
  recordingId: string
}

export function AttachedDocumentsCard({ recordingId }: AttachedDocumentsCardProps) {
  const { data: attachments = [] } = useAttachments(recordingId)
  const uploadMutation = useUploadAttachment(recordingId)
  const deleteMutation = useDeleteAttachment(recordingId)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [deleteTarget, setDeleteTarget] = useState<Attachment | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadMutation.mutate(file)
    }
    // Reset so user can select same file again
    e.target.value = ""
  }

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget.id)
      setDeleteTarget(null)
    }
  }

  return (
    <div className="rounded-xl bg-card p-5 shadow-[var(--shadow-card)] space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-headline">Attached Documents</h3>
        <Button
          variant="outline"
          size="sm"
          disabled={uploadMutation.isPending}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploadMutation.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Upload className="mr-1.5 h-3.5 w-3.5" />
          )}
          {uploadMutation.isPending ? "Uploading..." : "Upload"}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          className="hidden"
          aria-label="Upload document"
        />
      </div>

      {attachments.length === 0 ? (
        <p className="text-sm text-muted-foreground">No documents attached</p>
      ) : (
        <ul className="space-y-1">
          {attachments.map((attachment) => (
            <li
              key={attachment.id}
              className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-1.5 text-sm"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{attachment.filename}</span>
                {attachment.extraction_error && (
                  <Tooltip>
                    <TooltipTrigger render={<span className="inline-flex shrink-0" />}>
                      <AlertTriangle className="h-3.5 w-3.5 text-destructive/80" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Extraction error: {attachment.extraction_error}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
              <span className="ml-2 flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                {formatFileSize(attachment.file_size)}
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => setDeleteTarget(attachment)}
                  aria-label={`Delete ${attachment.filename}`}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove {deleteTarget?.filename}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleConfirmDelete}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
