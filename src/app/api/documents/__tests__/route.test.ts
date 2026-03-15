import { describe, it, expect } from "vitest"

describe("documents API routes", () => {
  it.todo("GET /api/documents returns list of documents")
  it.todo("GET /api/documents?type=prd filters by type")
  it.todo("GET /api/documents/[id] returns a single document")
  it.todo("GET /api/documents/[id] returns 404 for non-existent id")
  it.todo("POST /api/recordings/[id]/generate-prd triggers generation and returns 201")
  it.todo("POST /api/recordings/[id]/generate-diagram validates type field")
})
