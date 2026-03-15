"use client"

import { useRef, useState } from "react"
import { Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  RecordingPrepareSheet,
  type AudioPayload,
} from "@/components/recording/recording-prepare-sheet"

const ACCEPTED_FORMATS = ".webm,.mp3,.wav,.m4a,.mp4"

function getTitle(filename: string): string {
  const name = filename.replace(/\.[^.]+$/, "")
  return name.replace(/[-_]/g, " ").replace(/\s+/g, " ").trim() || "Uploaded recording"
}

export function UploadButton() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [pendingPayload, setPendingPayload] = useState<AudioPayload | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const recordingId = crypto.randomUUID()
    const title = getTitle(file.name)

    setPendingPayload({
      file,
      recordingId,
      title,
      durationMs: 0,
      source: "upload",
    })

    // Reset input so the same file can be re-selected later
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
      >
        <Upload data-icon="inline-start" className="size-4" />
        Upload Audio
      </Button>

      <RecordingPrepareSheet
        payload={pendingPayload}
        onClose={() => setPendingPayload(null)}
      />
    </>
  )
}
