import { NextRequest, NextResponse } from "next/server"
import { unlink } from "fs/promises"
import { join } from "path"

import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; attachmentId: string }> }
) {
  const { id, attachmentId } = await params
  const recording = getRecording(id)

  if (!recording) {
    return NextResponse.json({ error: "Recording not found" }, { status: 404 })
  }

  if (!recording.backendId) {
    return NextResponse.json(
      { error: "Recording has not been sent to backend" },
      { status: 400 }
    )
  }

  try {
    // Fetch attachment metadata to get filename for local cleanup
    let filename: string | null = null
    try {
      const metaRes = await fetch(
        `${BACKEND_URL}/recordings/${recording.backendId}/attachments`
      )
      if (metaRes.ok) {
        const attachments = await metaRes.json()
        const attachment = attachments.find(
          (a: { id: string; filename: string }) => a.id === attachmentId
        )
        if (attachment) {
          filename = attachment.filename
        }
      }
    } catch {
      // Best-effort metadata fetch; proceed with delete regardless
    }

    // Delete from Python backend
    const response = await fetch(
      `${BACKEND_URL}/recordings/${recording.backendId}/attachments/${attachmentId}`,
      { method: "DELETE" }
    )

    if (!response.ok && response.status !== 404) {
      return NextResponse.json(
        { error: "Failed to delete attachment" },
        { status: response.status }
      )
    }

    // Best-effort delete local file from public/recordings/{id}/docs/
    if (filename) {
      try {
        const localPath = join(
          process.cwd(),
          "public",
          "recordings",
          id,
          "docs",
          filename
        )
        await unlink(localPath)
      } catch {
        // File may not exist locally; ignore
      }
    }

    return new NextResponse(null, { status: 204 })
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    )
  }
}
