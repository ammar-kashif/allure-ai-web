import { RecordingHub } from "@/components/recording/recording-hub"
import { UploadButton } from "@/components/recording/upload-button"

export default function RecordingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Recordings</h2>
          <p className="text-muted-foreground">
            Manage your recordings and assign them to projects for transcription.
          </p>
        </div>
        <UploadButton />
      </div>
      <RecordingHub />
    </div>
  )
}
