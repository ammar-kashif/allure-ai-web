"use client"

import { useCallback, useRef, useState } from "react"
import { Upload, X } from "lucide-react"
import { toast } from "sonner"

import { cn, formatFileSize } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const ACCEPTED_TYPES = [".pdf", ".docx", ".txt"]
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const ACCEPT_STRING = ACCEPTED_TYPES.join(",")

interface FileDropZoneProps {
  files: File[]
  onFilesChange: (files: File[]) => void
}

export function FileDropZone({ files, onFilesChange }: FileDropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (incoming: FileList | File[]) => {
      const accepted: File[] = []
      for (const f of Array.from(incoming)) {
        const ext = `.${f.name.split(".").pop()?.toLowerCase()}`
        if (!ACCEPTED_TYPES.includes(ext)) continue
        if (f.size > MAX_FILE_SIZE) {
          toast.error("File too large", {
            description: `${f.name} exceeds 10MB limit`,
          })
          continue
        }
        accepted.push(f)
      }
      if (accepted.length > 0) {
        onFilesChange([...files, ...accepted])
      }
    },
    [files, onFilesChange]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragActive(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleFiles(e.target.files)
      }
      // Reset so user can select same file again
      e.target.value = ""
    },
    [handleFiles]
  )

  const removeFile = useCallback(
    (index: number) => {
      onFilesChange(files.filter((_, i) => i !== index))
    },
    [files, onFilesChange]
  )

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors",
          isDragActive
            ? "border-primary bg-primary/5 text-primary"
            : "border-muted-foreground/25 text-muted-foreground hover:border-muted-foreground/40"
        )}
      >
        <Upload className="h-5 w-5" />
        <span className="text-sm">Drop files here or click to browse</span>
        <span className="text-xs text-muted-foreground/60">
          PDF, DOCX, TXT
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT_STRING}
        onChange={handleInputChange}
        className="hidden"
        aria-label="Upload reference documents"
      />

      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-1.5 text-sm"
            >
              <span className="min-w-0 truncate">{file.name}</span>
              <span className="ml-2 flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                {formatFileSize(file.size)}
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    removeFile(index)
                  }}
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3 w-3" />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
