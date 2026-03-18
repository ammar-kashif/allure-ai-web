import { NextRequest, NextResponse } from "next/server"
import { writeFile, mkdir } from "fs/promises"
import { join } from "path"

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

    return NextResponse.json({ ok: true, files: savedFiles })
  } catch (error) {
    console.error("Failed to upload documents:", error)
    return NextResponse.json(
      { error: "Failed to upload documents" },
      { status: 500 }
    )
  }
}
