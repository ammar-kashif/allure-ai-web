import { describe, it, expect, vi, beforeEach } from "vitest"

const { mockListDocuments, mockGetDocument } = vi.hoisted(() => ({
  mockListDocuments: vi.fn(),
  mockGetDocument: vi.fn(),
}))

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
      readFileSync: vi.fn().mockReturnValue(""),
    },
    existsSync: vi.fn().mockReturnValue(true),
    mkdirSync: vi.fn(),
    readFileSync: vi.fn().mockReturnValue(""),
  }
})

vi.mock("@/lib/db/documents", () => ({
  listDocuments: (...args: unknown[]) => mockListDocuments(...args),
  getDocument: (...args: unknown[]) => mockGetDocument(...args),
  createDocument: vi.fn(),
  countDocuments: vi.fn(),
}))

import { GET } from "../route"
import { GET as GET_BY_ID } from "../[id]/route"
import { NextRequest } from "next/server"

function createRequest(url: string): NextRequest {
  return new NextRequest(new URL(url, "http://localhost:3000"))
}

describe("documents API routes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("GET /api/documents", () => {
    it("returns list of documents", async () => {
      const mockDocs = [
        {
          id: "doc-1",
          title: "Test PRD",
          type: "prd",
          content: "# PRD",
          sourceRecordingId: "rec-1",
          createdAt: "2026-03-15 00:00:00",
        },
      ]
      mockListDocuments.mockReturnValue(mockDocs)

      const request = createRequest("http://localhost:3000/api/documents")
      const response = await GET(request)
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual(mockDocs)
      expect(mockListDocuments).toHaveBeenCalledWith({ type: null })
    })

    it("filters by type query param", async () => {
      mockListDocuments.mockReturnValue([])

      const request = createRequest(
        "http://localhost:3000/api/documents?type=prd"
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      expect(mockListDocuments).toHaveBeenCalledWith({ type: "prd" })
    })
  })

  describe("GET /api/documents/[id]", () => {
    it("returns a single document", async () => {
      const mockDoc = {
        id: "doc-1",
        title: "Test PRD",
        type: "prd",
        content: "# PRD",
        sourceRecordingId: "rec-1",
        createdAt: "2026-03-15 00:00:00",
      }
      mockGetDocument.mockReturnValue(mockDoc)

      const request = createRequest(
        "http://localhost:3000/api/documents/doc-1"
      )
      const response = await GET_BY_ID(request, {
        params: Promise.resolve({ id: "doc-1" }),
      })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual(mockDoc)
    })

    it("returns 404 for non-existent id", async () => {
      mockGetDocument.mockReturnValue(null)

      const request = createRequest(
        "http://localhost:3000/api/documents/non-existent"
      )
      const response = await GET_BY_ID(request, {
        params: Promise.resolve({ id: "non-existent" }),
      })

      expect(response.status).toBe(404)
    })
  })
})

