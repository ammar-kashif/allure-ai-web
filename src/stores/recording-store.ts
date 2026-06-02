import { create } from "zustand"
import { persist } from "zustand/middleware"

export interface PendingRecording {
  recordingId: string
  defaultTitle: string
  durationMs: number
}

export interface RecordingState {
  isRecording: boolean
  currentRecordingId: string | null
  startedAt: number | null // epoch ms
  elapsedSeconds: number
  /** Flag set on hydration if store says recording but no active MediaRecorder */
  needsRecovery: boolean
  /** Post-recording dialog state (ephemeral, not persisted) */
  showPostRecordingDialog: boolean
  pendingRecording: PendingRecording | null
}

export interface RecordingActions {
  startRecording: (id: string) => void
  stopRecording: () => void
  setElapsed: (seconds: number) => void
  setNeedsRecovery: (needs: boolean) => void
  reset: () => void
  openPostRecordingDialog: (data: PendingRecording) => void
  closePostRecordingDialog: () => void
}

const initialState: RecordingState = {
  isRecording: false,
  currentRecordingId: null,
  startedAt: null,
  elapsedSeconds: 0,
  needsRecovery: false,
  showPostRecordingDialog: false,
  pendingRecording: null,
}

export const useRecordingStore = create<RecordingState & RecordingActions>()(
  persist(
    (set) => ({
      ...initialState,

      startRecording: (id: string) =>
        set({
          isRecording: true,
          currentRecordingId: id,
          startedAt: Date.now(),
          elapsedSeconds: 0,
          needsRecovery: false,
        }),

      stopRecording: () =>
        set({
          isRecording: false,
          currentRecordingId: null,
          startedAt: null,
          elapsedSeconds: 0,
          needsRecovery: false,
        }),

      setElapsed: (seconds: number) => set({ elapsedSeconds: seconds }),

      setNeedsRecovery: (needs: boolean) => set({ needsRecovery: needs }),

      reset: () => set(initialState),

      openPostRecordingDialog: (data: PendingRecording) =>
        set({ showPostRecordingDialog: true, pendingRecording: data }),

      closePostRecordingDialog: () =>
        set({ showPostRecordingDialog: false, pendingRecording: null }),
    }),
    {
      name: "allure-recording",
      // Only persist recording-in-progress fields, not ephemeral dialog state
      partialize: (state) => ({
        isRecording: state.isRecording,
        currentRecordingId: state.currentRecordingId,
        startedAt: state.startedAt,
        elapsedSeconds: state.elapsedSeconds,
        needsRecovery: state.needsRecovery,
      }),
      // On hydration, check if isRecording was left true (indicates crash)
      onRehydrateStorage: () => (state) => {
        if (state?.isRecording) {
          state.needsRecovery = true
          state.isRecording = false
        }
      },
    }
  )
)

