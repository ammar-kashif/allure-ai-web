import { describe, it, expect, vi, beforeEach } from "vitest"

const { mockPrepare } = vi.hoisted(() => {
  const mockRun = vi.fn()
  const mockGet = vi.fn()
  const mockAll = vi.fn().mockReturnValue([])
  const mockPrepare = vi.fn().mockReturnValue({
    run: mockRun,
    get: mockGet,
    all: mockAll,
  })
  return { mockPrepare, mockRun, mockGet, mockAll }
})

const mockDb = {
  prepare: mockPrepare,
}

vi.mock("./index", () => ({
  getDb: () => mockDb,
}))

import {
  createDocument,
  getDocument,
  listDocuments,
  countDocuments,
} from "./documents"

describe("documents db module", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Restore default return values after clearAllMocks
    mockPrepare.mockReturnValue({
      run: vi.fn(),
      get: vi.fn(),
      all: vi.fn().mockReturnValue([]),
    })
  })

  it("createDocument inserts a document and returns it with generated id", () => {
    const mockRow = {
      id: "test-uuid",
      title: "Test PRD",
      type: "prd",
      content: "# PRD Content",
      source_recording_id: "rec-1",
      created_at: "2026-03-15 00:00:00",
    }

    const mockRun = vi.fn()
    const mockGet = vi.fn().mockReturnValue(mockRow)
    mockPrepare.mockReturnValue({ run: mockRun, get: mockGet, all: vi.fn() })

    const doc = createDocument({
      title: "Test PRD",
      type: "prd",
      content: "# PRD Content",
      sourceRecordingId: "rec-1",
    })

    expect(mockPrepare).toHaveBeenCalledWith(
      expect.stringContaining("INSERT INTO documents")
    )
    expect(doc.title).toBe("Test PRD")
    expect(doc.type).toBe("prd")
    expect(doc.sourceRecordingId).toBe("rec-1")
  })

  it("getDocument returns a document by id", () => {
    const mockRow = {
      id: "doc-1",
      title: "Test Doc",
      type: "erd",
      content: "erDiagram",
      source_recording_id: "rec-1",
      created_at: "2026-03-15 00:00:00",
    }

    const mockGet = vi.fn().mockReturnValue(mockRow)
    mockPrepare.mockReturnValue({ run: vi.fn(), get: mockGet, all: vi.fn() })

    const doc = getDocument("doc-1")

    expect(doc).not.toBeNull()
    expect(doc!.id).toBe("doc-1")
    expect(doc!.type).toBe("erd")
    expect(doc!.sourceRecordingId).toBe("rec-1")
  })

  it("getDocument returns null for non-existent id", () => {
    const mockGet = vi.fn().mockReturnValue(undefined)
    mockPrepare.mockReturnValue({ run: vi.fn(), get: mockGet, all: vi.fn() })

    const doc = getDocument("non-existent")

    expect(doc).toBeNull()
  })

  it("listDocuments returns all documents ordered by created_at DESC", () => {
    const mockRows = [
      {
        id: "doc-2",
        title: "Doc 2",
        type: "prd",
        content: "content 2",
        source_recording_id: "rec-1",
        created_at: "2026-03-15 01:00:00",
      },
      {
        id: "doc-1",
        title: "Doc 1",
        type: "erd",
        content: "content 1",
        source_recording_id: "rec-1",
        created_at: "2026-03-15 00:00:00",
      },
    ]

    const mockAll = vi.fn().mockReturnValue(mockRows)
    mockPrepare.mockReturnValue({ run: vi.fn(), get: vi.fn(), all: mockAll })

    const docs = listDocuments()

    expect(docs).toHaveLength(2)
    expect(docs[0].id).toBe("doc-2")
    expect(docs[1].id).toBe("doc-1")
    expect(mockPrepare).toHaveBeenCalledWith(
      expect.stringContaining("ORDER BY created_at DESC")
    )
  })

  it("listDocuments filters by type when type param provided", () => {
    const mockRows = [
      {
        id: "doc-1",
        title: "PRD Doc",
        type: "prd",
        content: "content",
        source_recording_id: "rec-1",
        created_at: "2026-03-15 00:00:00",
      },
    ]

    const mockAll = vi.fn().mockReturnValue(mockRows)
    mockPrepare.mockReturnValue({ run: vi.fn(), get: vi.fn(), all: mockAll })

    const docs = listDocuments({ type: "prd" })

    expect(docs).toHaveLength(1)
    expect(mockPrepare).toHaveBeenCalledWith(
      expect.stringContaining("WHERE type = ?")
    )
    expect(mockAll).toHaveBeenCalledWith("prd")
  })

  it("countDocuments returns the total number of documents", () => {
    const mockGet = vi.fn().mockReturnValue({ count: 5 })
    mockPrepare.mockReturnValue({ run: vi.fn(), get: mockGet, all: vi.fn() })

    const count = countDocuments()

    expect(count).toBe(5)
    expect(mockPrepare).toHaveBeenCalledWith(
      expect.stringContaining("COUNT(*)")
    )
  })
})

