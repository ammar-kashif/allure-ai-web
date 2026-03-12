import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// Use vi.hoisted so mocks are available in vi.mock factory (which is hoisted)
const { mockGetRecordings, mockCreateRecording, mockUpdateRecording } =
  vi.hoisted(() => ({
    mockGetRecordings: vi.fn(),
    mockCreateRecording: vi.fn(),
    mockUpdateRecording: vi.fn(),
  }))

// Mock better-sqlite3 before any imports
vi.mock("better-sqlite3", () => ({
  default: vi.fn(() => ({
    prepare: vi.fn().mockReturnValue({
      run: vi.fn(),
      get: vi.fn(),
      all: vi.fn(),
    }),
    exec: vi.fn(),
    pragma: vi.fn(),
  })),
}))

vi.mock(import("fs"), async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: {
      ...actual,
      existsSync: vi.fn().mockReturnValue(true),
      mkdirSync: vi.fn(),
      writeFileSync: vi.fn(),
      readFileSync: vi.fn().mockReturnValue(""),
    },
    existsSync: vi.fn().mockReturnValue(true),
    mkdirSync: vi.fn(),
    writeFileSync: vi.fn(),
    readFileSync: vi.fn().mockReturnValue(""),
  }
})

vi.mock("@/lib/db/recordings", () => ({
  getRecordings: (...args: unknown[]) => mockGetRecordings(...args),
  getRecording: vi.fn(),
  createRecording: (...args: unknown[]) => mockCreateRecording(...args),
  updateRecording: (...args: unknown[]) => mockUpdateRecording(...args),
}))

import { GET, POST } from "../route"
import { NextRequest } from "next/server"

function createRequest(url: string, init?: RequestInit): NextRequest {
  return new NextRequest(new URL(url, "http://localhost:3000"), init)
}

describe("recordings API route", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("GET /api/recordings", () => {
    it("returns recordings list from local SQLite", async () => {
      const mockRecordings = [
        {
          id: "rec-1",
          title: "Test Recording",
          durationMs: 5000,
          filePath: "/path/to/file.webm",
          status: "unassigned",
          projectId: null,
          backendId: null,
          errorMessage: null,
          createdAt: "2026-03-12 00:00:00",
          updatedAt: "2026-03-12 00:00:00",
        },
      ]
      mockGetRecordings.mockReturnValue(mockRecordings)

      const request = createRequest("http://localhost:3000/api/recordings")
      const response = await GET(request)
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual(mockRecordings)
      expect(mockGetRecordings).toHaveBeenCalledWith(undefined)
    })

    it("filters recordings by status query param", async () => {
      mockGetRecordings.mockReturnValue([])

      const request = createRequest(
        "http://localhost:3000/api/recordings?status=processing"
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      expect(mockGetRecordings).toHaveBeenCalledWith("processing")
    })
  })

  describe("POST /api/recordings", () => {
    it("saves file locally and creates DB record", async () => {
      const mockRecording = {
        id: "rec-1",
        title: "Test Recording",
        durationMs: 5000,
        filePath: "/Users/ammarkashif/Documents/Code/allure-ai/public/recordings/rec-1.webm",
        status: "unassigned",
        projectId: null,
        backendId: null,
        errorMessage: null,
        createdAt: "2026-03-12 00:00:00",
        updatedAt: "2026-03-12 00:00:00",
      }
      mockCreateRecording.mockReturnValue(mockRecording)

      const formData = new FormData()
      formData.append(
        "file",
        new Blob(["audio data"], { type: "audio/webm" }),
        "recording.webm"
      )
      formData.append("recordingId", "rec-1")
      formData.append("title", "Test Recording")
      formData.append("durationMs", "5000")

      const request = createRequest("http://localhost:3000/api/recordings", {
        method: "POST",
        body: formData,
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(201)
      expect(mockCreateRecording).toHaveBeenCalledWith({
        id: "rec-1",
        title: "Test Recording",
        durationMs: 5000,
        filePath: expect.stringContaining("rec-1.webm"),
      })
      expect(data.id).toBe("rec-1")
    })

    it("POST with projectId proxies upload to FastAPI backend", async () => {
      const mockRecording = {
        id: "rec-2",
        title: "Test Recording 2",
        durationMs: 3000,
        filePath: "/path/rec-2.webm",
        status: "unassigned",
        projectId: null,
        backendId: null,
        errorMessage: null,
        createdAt: "2026-03-12 00:00:00",
        updatedAt: "2026-03-12 00:00:00",
      }
      mockCreateRecording.mockReturnValue(mockRecording)
      mockUpdateRecording.mockReturnValue({
        ...mockRecording,
        status: "processing",
      })

      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "backend-123" }), { status: 200 })
        )

      const formData = new FormData()
      formData.append(
        "file",
        new Blob(["audio data"], { type: "audio/webm" }),
        "recording.webm"
      )
      formData.append("recordingId", "rec-2")
      formData.append("title", "Test Recording 2")
      formData.append("durationMs", "3000")
      formData.append("projectId", "proj-1")

      const request = createRequest("http://localhost:3000/api/recordings", {
        method: "POST",
        body: formData,
      })

      const response = await POST(request)

      expect(response.status).toBe(201)
      expect(mockUpdateRecording).toHaveBeenCalledWith("rec-2", {
        projectId: "proj-1",
        status: "processing",
      })
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:8000/recordings",
        expect.objectContaining({
          method: "POST",
          body: expect.any(FormData),
        })
      )
      expect(mockUpdateRecording).toHaveBeenCalledWith("rec-2", {
        backendId: "backend-123",
      })

      fetchSpy.mockRestore()
    })

    it("POST without projectId does not proxy to backend", async () => {
      const mockRecording = {
        id: "rec-3",
        title: "Test Recording 3",
        durationMs: 2000,
        filePath: "/path/rec-3.webm",
        status: "unassigned",
        projectId: null,
        backendId: null,
        errorMessage: null,
        createdAt: "2026-03-12 00:00:00",
        updatedAt: "2026-03-12 00:00:00",
      }
      mockCreateRecording.mockReturnValue(mockRecording)

      const fetchSpy = vi.spyOn(globalThis, "fetch")

      const formData = new FormData()
      formData.append(
        "file",
        new Blob(["audio data"], { type: "audio/webm" }),
        "recording.webm"
      )
      formData.append("recordingId", "rec-3")
      formData.append("title", "Test Recording 3")
      formData.append("durationMs", "2000")

      const request = createRequest("http://localhost:3000/api/recordings", {
        method: "POST",
        body: formData,
      })

      const response = await POST(request)

      expect(response.status).toBe(201)
      expect(mockCreateRecording).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(mockUpdateRecording).not.toHaveBeenCalled()

      fetchSpy.mockRestore()
    })
  })
})
