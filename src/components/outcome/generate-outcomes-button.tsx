"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useExtract } from "@/hooks/use-outcomes"

interface GenerateOutcomesButtonProps {
  recordingId: string
  label?: string
}

export function GenerateOutcomesButton({
  recordingId,
  label = "Generate Outcomes",
}: GenerateOutcomesButtonProps) {
  const [error, setError] = useState<string | null>(null)
  const { mutate, isPending } = useExtract(recordingId)

  return (
    <div>
      <Button
        onClick={() => {
          setError(null)
          mutate(undefined, {
            onError: (err) => setError(err.message || "Failed to trigger extraction"),
          })
        }}
        disabled={isPending}
        size="sm"
      >
        {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {label}
      </Button>
      {error && (
        <p className="mt-2 text-sm text-destructive">{error}</p>
      )}
    </div>
  )
}

