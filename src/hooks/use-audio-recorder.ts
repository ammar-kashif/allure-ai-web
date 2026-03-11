"use client"

import { useCallback, useEffect, useRef } from "react"
import { toast } from "sonner"

import { useRecordingStore } from "@/stores/recording-store"
import {
  clearAudioChunks,
  getAudioChunks,
  saveAudioChunk,
} from "@/lib/audio/chunk-store"
import { checkForRecovery, discardRecovery, recoverRecording } from "@/lib/audio/recovery"
import { generateRecordingTitle } from "@/lib/utils"

/**
 * Module-level MediaRecorder ref. Survives React re-renders and navigation.
 * The FAB lives in root layout which never unmounts, but this is extra safety.
 */
let mediaRecorderRef: MediaRecorder | null = null
let mediaStreamRef: MediaStream | null = null

export interface AudioRecorderResult {
  blob: Blob
  recordingId: string
  title: string
  durationMs: number
}

export function useAudioRecorder() {
  const {
    isRecording,
    currentRecordingId,
    startedAt,
    elapsedSeconds,
    needsRecovery,
    startRecording: storeStart,
    stopRecording: storeStop,
    setElapsed,
    setNeedsRecovery,
  } = useRecordingStore()

  const onRecordingCompleteRef = useRef<
    ((result: AudioRecorderResult) => void) | null
  >(null)

  // Elapsed time counter
  useEffect(() => {
    if (!isRecording || !startedAt) return

    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000)
      setElapsed(elapsed)
    }, 1000)

    return () => clearInterval(interval)
  }, [isRecording, startedAt, setElapsed])

  // Crash recovery check on mount
  useEffect(() => {
    if (!needsRecovery) return

    checkForRecovery().then((result) => {
      if (!result.hasRecovery) {
        setNeedsRecovery(false)
        return
      }

      toast.info("Recovered incomplete recording", {
        description: "A previous recording was interrupted. Would you like to recover it?",
        duration: 10000,
        action: {
          label: "Recover",
          onClick: async () => {
            for (const id of result.recordingIds) {
              const blob = await recoverRecording(id)
              if (blob) {
                toast.success("Recording recovered", {
                  description: `Recovered ${(blob.size / 1024).toFixed(0)} KB of audio`,
                })
              }
              await clearAudioChunks(id)
            }
            setNeedsRecovery(false)
          },
        },
        cancel: {
          label: "Discard",
          onClick: async () => {
            for (const id of result.recordingIds) {
              await discardRecovery(id)
            }
            setNeedsRecovery(false)
          },
        },
      })
    })
  }, [needsRecovery, setNeedsRecovery])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef = stream

      const recordingId = crypto.randomUUID()
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef = recorder

      recorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          await saveAudioChunk(recordingId, event.data)
        }
      }

      recorder.onerror = () => {
        toast.error("Recording error", {
          description: "An error occurred during recording.",
        })
        stopRecording()
      }

      recorder.start(3000) // 3-second chunks
      storeStart(recordingId)
    } catch (error) {
      const message =
        error instanceof DOMException && error.name === "NotAllowedError"
          ? "Microphone access denied. Please allow microphone access in your browser settings."
          : "Failed to start recording. Please check your microphone."
      toast.error("Recording failed", { description: message })
    }
  }, [storeStart])

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef
    const recId = useRecordingStore.getState().currentRecordingId
    const recordingStartedAt = useRecordingStore.getState().startedAt

    if (!recorder || !recId) return

    return new Promise<AudioRecorderResult | null>((resolve) => {
      recorder.onstop = async () => {
        // Assemble final blob from IndexedDB chunks
        const chunks = await getAudioChunks(recId)
        const blob = new Blob(chunks, { type: recorder.mimeType })
        await clearAudioChunks(recId)

        // Stop all tracks
        mediaStreamRef?.getTracks().forEach((t) => t.stop())
        mediaRecorderRef = null
        mediaStreamRef = null

        const durationMs = recordingStartedAt
          ? Date.now() - recordingStartedAt
          : 0

        const result: AudioRecorderResult = {
          blob,
          recordingId: recId,
          title: generateRecordingTitle(
            recordingStartedAt ? new Date(recordingStartedAt) : new Date()
          ),
          durationMs,
        }

        storeStop()

        if (onRecordingCompleteRef.current) {
          onRecordingCompleteRef.current(result)
        }

        resolve(result)
      }

      if (recorder.state !== "inactive") {
        recorder.stop()
      } else {
        storeStop()
        resolve(null)
      }
    })
  }, [storeStop])

  return {
    isRecording,
    elapsedSeconds,
    currentRecordingId,
    startRecording,
    stopRecording,
    onRecordingCompleteRef,
  }
}
