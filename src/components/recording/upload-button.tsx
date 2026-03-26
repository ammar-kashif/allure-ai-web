"use client"

import { useRef } from "react"
import { Upload } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { useUploadRecording } from "@/hooks/use-recordings"

const ACCEPTED_FORMATS = ".webm,.mp3,.wav,.m4a,.mp4,.mov"
const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB

function getTitle(filename: string): string {
  const name = filename.replace(/\.[^.]+$/, "")
  return name.replace(/[-_]/g, " ").replace(/\s+/g, " ").trim() || "Uploaded recording"
}

export function UploadButton() {
  const inputRef = useRef<HTMLInputElement>(null)
  const uploadRecording = useUploadRecording()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > MAX_FILE_SIZE) {
      toast.error("File too large", {
        description: "Maximum file size is 500MB. Please use a shorter recording or compress the file.",
      })
      return
    }

    const recordingId = crypto.randomUUID()
    const title = getTitle(file.name)

    const formData = new FormData()
    formData.append("file", file, file.name)
    formData.append("recordingId", recordingId)
    formData.append("title", title)
    formData.append("durationMs", "0")

    uploadRecording.mutate(formData, {
      onSuccess: () => {
        toast.success("File uploaded", {
          description: `"${title}" is ready for project assignment.`,
        })
      },
      onError: () => {
        toast.error("Upload failed", {
          description: "The file could not be uploaded. Please try again.",
        })
      },
    })

    // Reset input so the same file can be re-selected
    if (inputRef.current) inputRef.current.value = ""
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_FORMATS}
        onChange={handleFileChange}
        className="hidden"
        aria-hidden="true"
      />
      <Button
        variant="outline"
        size="default"
        onClick={() => inputRef.current?.click()}
        disabled={uploadRecording.isPending}
      >
        <Upload data-icon="inline-start" className="size-4" />
        {uploadRecording.isPending ? "Uploading..." : "Upload File"}
      </Button>
    </>
  )
}
