import { NextRequest, NextResponse } from "next/server"
import { writeFile, mkdir, readFile } from "fs/promises"
import { join } from "path"

import { getRecording } from "@/lib/db/recordings"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: recordingId } = await params

    if (!recordingId) {
      return NextResponse.json(
        { error: "Recording ID is required" },
        { status: 400 }
      )
    }

    const formData = await request.formData()
    const files = formData.getAll("files") as File[]

    if (files.length === 0) {
      return NextResponse.json(
        { error: "No files provided" },
        { status: 400 }
      )
    }

    // Save files to public/recordings/{recordingId}/docs/
    const docsDir = join(process.cwd(), "public", "recordings", recordingId, "docs")
    await mkdir(docsDir, { recursive: true })

    const savedFiles: { name: string; size: number; path: string }[] = []

    // Check if recording has a backend ID for extraction
    const recording = getRecording(recordingId)
    const backendId = recording?.backendId

    for (const file of files) {
      const buffer = Buffer.from(await file.arrayBuffer())
      const filePath = join(docsDir, file.name)
      await writeFile(filePath, buffer)

      savedFiles.push({
        name: file.name,
        size: file.size,
        path: `/recordings/${recordingId}/docs/${file.name}`,
      })

      // Also POST to Python backend for text extraction and DB storage
      if (backendId) {
        try {
          const fileBuffer = await readFile(filePath)
          const blob = new Blob([fileBuffer], { type: file.type || "application/octet-stream" })
          const backendForm = new FormData()
          backendForm.append("file", blob, file.name)

          await fetch(
            `${BACKEND_URL}/recordings/${backendId}/attachments`,
            {
              method: "POST",
              body: backendForm,
            }
          )
        } catch (extractionError) {
          // Graceful degradation: file is saved to disk even if extraction fails
          console.error(`Backend extraction failed for ${file.name}:`, extractionError)
        }
      }
    }

    return NextResponse.json({ ok: true, files: savedFiles })
  } catch (error) {
    console.error("Failed to upload documents:", error)
    return NextResponse.json(
      { error: "Failed to upload documents" },
      { status: 500 }
    )
  }
}
