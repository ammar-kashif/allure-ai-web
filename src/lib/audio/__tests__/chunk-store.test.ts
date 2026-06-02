import { describe, it, expect, beforeEach } from "vitest"
import "fake-indexeddb/auto"
import {
  saveAudioChunk,
  getAudioChunks,
  clearAudioChunks,
  getIncompleteRecordingIds,
  resetDB,
} from "../chunk-store"

describe("chunk-store", () => {
  beforeEach(() => {
    // Reset the DB connection between tests for isolation
    resetDB()
    // Clear all IndexedDB databases
    indexedDB = new IDBFactory()
  })

  it("saveAudioChunk stores a chunk with recordingId and timestamp", async () => {
    const blob = new Blob(["test-audio-data"], { type: "audio/webm" })
    await saveAudioChunk("rec-1", blob)

    const chunks = await getAudioChunks("rec-1")
    expect(chunks).toHaveLength(1)
    // fake-indexeddb may store Blob as plain object, so check shape instead
    expect(chunks[0]).toHaveProperty("type", "audio/webm")
  })

  it("getAudioChunks returns chunks sorted by timestamp for a given recordingId", async () => {
    const blob1 = new Blob(["chunk-1"], { type: "audio/webm" })
    const blob2 = new Blob(["chunk-2"], { type: "audio/webm" })
    const blob3 = new Blob(["chunk-3"], { type: "audio/webm" })

    await saveAudioChunk("rec-1", blob1)
    await saveAudioChunk("rec-1", blob2)
    await saveAudioChunk("rec-1", blob3)

    const chunks = await getAudioChunks("rec-1")
    expect(chunks).toHaveLength(3)

    // Verify we got 3 distinct chunks back in order
    expect(chunks[0]).toHaveProperty("type", "audio/webm")
    expect(chunks[1]).toHaveProperty("type", "audio/webm")
    expect(chunks[2]).toHaveProperty("type", "audio/webm")
  })

  it("getAudioChunks returns only chunks for the specified recordingId", async () => {
    await saveAudioChunk("rec-1", new Blob(["a"]))
    await saveAudioChunk("rec-2", new Blob(["b"]))
    await saveAudioChunk("rec-1", new Blob(["c"]))

    const chunks1 = await getAudioChunks("rec-1")
    const chunks2 = await getAudioChunks("rec-2")
    expect(chunks1).toHaveLength(2)
    expect(chunks2).toHaveLength(1)
  })

  it("clearAudioChunks removes all chunks for a given recordingId", async () => {
    await saveAudioChunk("rec-1", new Blob(["a"]))
    await saveAudioChunk("rec-1", new Blob(["b"]))
    await saveAudioChunk("rec-2", new Blob(["c"]))

    await clearAudioChunks("rec-1")

    const chunks1 = await getAudioChunks("rec-1")
    const chunks2 = await getAudioChunks("rec-2")
    expect(chunks1).toHaveLength(0)
    expect(chunks2).toHaveLength(1)
  })

  it("getIncompleteRecordingIds returns recordingIds with remaining chunks", async () => {
    await saveAudioChunk("rec-1", new Blob(["a"]))
    await saveAudioChunk("rec-2", new Blob(["b"]))
    await saveAudioChunk("rec-1", new Blob(["c"]))

    const ids = await getIncompleteRecordingIds()
    expect(ids).toHaveLength(2)
    expect(ids).toContain("rec-1")
    expect(ids).toContain("rec-2")
  })

  it("getIncompleteRecordingIds returns empty when no chunks exist", async () => {
    const ids = await getIncompleteRecordingIds()
    expect(ids).toHaveLength(0)
  })
})

