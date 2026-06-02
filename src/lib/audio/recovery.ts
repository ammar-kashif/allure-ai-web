import {
  clearAudioChunks,
  getAudioChunks,
  getIncompleteRecordingIds,
} from "./chunk-store"
import { useRecordingStore } from "@/stores/recording-store"

interface RecoveryCheck {
  hasRecovery: boolean
  recordingIds: string[]
}

/**
 * Check for recordings that were interrupted (browser crash, tab close, etc.).
 * Looks at both Zustand persisted state and IndexedDB for incomplete recordings.
 */
export async function checkForRecovery(): Promise<RecoveryCheck> {
  const store = useRecordingStore.getState()
  const incompleteIds = await getIncompleteRecordingIds()

  // Merge: store might know about a recording that IndexedDB also has chunks for
  const allIds = new Set(incompleteIds)
  if (store.currentRecordingId && store.needsRecovery) {
    allIds.add(store.currentRecordingId)
  }

  const recordingIds = Array.from(allIds)
  return {
    hasRecovery: recordingIds.length > 0,
    recordingIds,
  }
}

/**
 * Reassemble chunks from IndexedDB into a single audio Blob.
 * Returns null if no chunks found.
 */
export async function recoverRecording(
  recordingId: string
): Promise<Blob | null> {
  const chunks = await getAudioChunks(recordingId)
  if (chunks.length === 0) return null
  return new Blob(chunks, { type: "audio/webm;codecs=opus" })
}

/**
 * Discard a recovered recording: clear IndexedDB chunks and reset store.
 */
export async function discardRecovery(recordingId: string): Promise<void> {
  await clearAudioChunks(recordingId)
  const store = useRecordingStore.getState()
  if (store.currentRecordingId === recordingId) {
    store.reset()
  }
}

