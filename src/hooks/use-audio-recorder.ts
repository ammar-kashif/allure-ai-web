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
 * Module-level refs. Survive React re-renders and navigation.
 * The FAB lives in root layout which never unmounts, but this is extra safety.
 */
let mediaRecorderRef: MediaRecorder | null = null
let mediaStreamRef: MediaStream | null = null
let displayStreamRef: MediaStream | null = null
let audioContextRef: AudioContext | null = null

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
      // 1. Get microphone audio
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef = micStream

      // 2. Try to get system/tab audio via getDisplayMedia
      let mixedStream: MediaStream = micStream
      try {
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          audio: true,
          video: false, // We only want audio, not screen video
        })
        displayStreamRef = displayStream

        // Check if we actually got audio tracks (user might not have shared audio)
        const displayAudioTracks = displayStream.getAudioTracks()
        if (displayAudioTracks.length > 0) {
          // 3. Mix mic + system audio using Web Audio API
          const audioContext = new AudioContext()
          audioContextRef = audioContext

          const micSource = audioContext.createMediaStreamSource(micStream)
          const displaySource = audioContext.createMediaStreamSource(
            new MediaStream(displayAudioTracks)
          )
          const destination = audioContext.createMediaStreamDestination()

          micSource.connect(destination)
          displaySource.connect(destination)

          mixedStream = destination.stream

          // Stop the video track if browser included one despite video: false
          displayStream.getVideoTracks().forEach((t) => t.stop())

          // If the user stops sharing the tab, stop the recording
          displayAudioTracks[0].onended = () => {
            if (mediaRecorderRef?.state === "recording") {
              toast.info("Tab sharing ended", {
                description: "Recording will continue with microphone only.",
              })
            }
          }
        } else {
          // User shared screen but no audio — continue with mic only
          displayStream.getTracks().forEach((t) => t.stop())
          displayStreamRef = null
        }
      } catch {
        // User cancelled the display picker or browser doesn't support it
        // Continue with mic-only recording
        displayStreamRef = null
      }

      const recordingId = crypto.randomUUID()
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"

      const recorder = new MediaRecorder(mixedStream, { mimeType })
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

      toast.success("Recording started", {
        description: displayStreamRef
          ? "Capturing microphone + system audio"
          : "Capturing microphone only",
      })
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

        // Stop all tracks and clean up
        mediaStreamRef?.getTracks().forEach((t) => t.stop())
        displayStreamRef?.getTracks().forEach((t) => t.stop())
        audioContextRef?.close().catch(() => {})
        mediaRecorderRef = null
        mediaStreamRef = null
        displayStreamRef = null
        audioContextRef = null

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
