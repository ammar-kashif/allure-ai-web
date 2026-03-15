import { describe, it, expect } from "vitest"

describe("documents db module", () => {
  it.todo("createDocument inserts a document and returns it with generated id")
  it.todo("getDocument returns a document by id")
  it.todo("getDocument returns null for non-existent id")
  it.todo("listDocuments returns all documents ordered by created_at DESC")
  it.todo("listDocuments filters by type when type param provided")
  it.todo("countDocuments returns the total number of documents")
})
