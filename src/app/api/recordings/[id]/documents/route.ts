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

    // Step 1: Save all files to disk first (graceful degradation -- files always persisted)
    for (const file of files) {
      const buffer = Buffer.from(await file.arrayBuffer())
      const filePath = join(docsDir, file.name)
      await writeFile(filePath, buffer)

      savedFiles.push({
        name: file.name,
        size: file.size,
        path: `/recordings/${recordingId}/docs/${file.name}`,
      })
    }

    // Step 2: Resolve backendId with retry (handles race condition when
    // documents are uploaded from post-recording dialog before backend
    // has finished creating the recording)
    const recording = getRecording(recordingId)
    let backendId = recording?.backendId

    if (!backendId) {
      for (let attempt = 0; attempt < 5; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        const freshRecording = getRecording(recordingId)
        if (freshRecording?.backendId) {
          backendId = freshRecording.backendId
          break
        }
      }
    }

    // Step 3: Forward saved files to backend for text extraction (if backendId resolved)
    if (backendId) {
      for (const saved of savedFiles) {
        try {
          const filePath = join(docsDir, saved.name)
          const fileBuffer = await readFile(filePath)
          const blob = new Blob([fileBuffer], { type: "application/octet-stream" })
          const backendForm = new FormData()
          backendForm.append("file", blob, saved.name)

          await fetch(
            `${BACKEND_URL}/recordings/${backendId}/attachments`,
            {
              method: "POST",
              body: backendForm,
            }
          )
        } catch (extractionError) {
          // Graceful degradation: file is saved to disk even if extraction fails
          console.error(`Backend extraction failed for ${saved.name}:`, extractionError)
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

