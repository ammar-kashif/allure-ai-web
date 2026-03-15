import { RecordingHub } from "@/components/recording/recording-hub"
import { UploadButton } from "@/components/recording/upload-button"

export default function RecordingsPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em]">Recordings</h1>
          <p className="mt-1 text-[0.9375rem] text-muted-foreground">
            Manage your recordings and assign them to projects for transcription.
          </p>
        </div>
        <UploadButton />
      </div>
      <RecordingHub />
    </div>
  )
}
