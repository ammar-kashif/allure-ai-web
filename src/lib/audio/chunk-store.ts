import { openDB, type DBSchema, type IDBPDatabase } from "idb"

interface AudioChunkRecord {
  id?: number
  recordingId: string
  chunk: Blob
  timestamp: number
}

interface AllureAudioDB extends DBSchema {
  chunks: {
    key: number
    value: AudioChunkRecord
    indexes: {
      "by-recording": string
    }
  }
}

const DB_NAME = "allure-audio"
const DB_VERSION = 1

let dbPromise: Promise<IDBPDatabase<AllureAudioDB>> | null = null

function getDB(): Promise<IDBPDatabase<AllureAudioDB>> {
  if (!dbPromise) {
    dbPromise = openDB<AllureAudioDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const store = db.createObjectStore("chunks", {
          keyPath: "id",
          autoIncrement: true,
        })
        store.createIndex("by-recording", "recordingId")
      },
    })
  }
  return dbPromise
}

/** Store an audio chunk for a given recording. */
export async function saveAudioChunk(
  recordingId: string,
  chunk: Blob
): Promise<void> {
  const db = await getDB()
  await db.add("chunks", {
    recordingId,
    chunk,
    timestamp: Date.now(),
  })
}

/** Retrieve all audio chunks for a recording, sorted by timestamp. */
export async function getAudioChunks(recordingId: string): Promise<Blob[]> {
  const db = await getDB()
  const records = await db.getAllFromIndex("chunks", "by-recording", recordingId)
  records.sort((a, b) => a.timestamp - b.timestamp)
  return records.map((r) => r.chunk)
}

/** Delete all chunks for a given recording. */
export async function clearAudioChunks(recordingId: string): Promise<void> {
  const db = await getDB()
  const tx = db.transaction("chunks", "readwrite")
  const index = tx.store.index("by-recording")
  let cursor = await index.openCursor(recordingId)
  while (cursor) {
    await cursor.delete()
    cursor = await cursor.continue()
  }
  await tx.done
}

/** Get IDs of recordings that still have chunks in IndexedDB (incomplete/crashed). */
export async function getIncompleteRecordingIds(): Promise<string[]> {
  const db = await getDB()
  const allRecords = await db.getAll("chunks")
  const ids = new Set(allRecords.map((r) => r.recordingId))
  return Array.from(ids)
}

/** Reset the DB connection (useful for tests). */
export function resetDB(): void {
  dbPromise = null
}

