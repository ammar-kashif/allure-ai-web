import { create } from "zustand"
import { persist } from "zustand/middleware"

/**
 * Tracks the currently-active bot meeting recording so the banner survives
 * page navigation and reloads. Kept separate from the native-recording store
 * so the two flows don't collide.
 *
 * Only one bot session can be active at a time (the bot itself is
 * single-tenant: globalJobStore.isBusy() goes to 1 on dispatch).
 */
export interface BotMeetingSessionState {
  recordingId: string | null
  title: string | null
  meetingUrl: string | null
  startedAt: number | null
}

export interface BotMeetingSessionActions {
  setActive: (data: {
    recordingId: string
    title: string | null
    meetingUrl: string
  }) => void
  clear: () => void
}

const initialState: BotMeetingSessionState = {
  recordingId: null,
  title: null,
  meetingUrl: null,
  startedAt: null,
}

export const useBotMeetingStore = create<
  BotMeetingSessionState & BotMeetingSessionActions
>()(
  persist(
    (set) => ({
      ...initialState,
      setActive: ({ recordingId, title, meetingUrl }) =>
        set({
          recordingId,
          title,
          meetingUrl,
          startedAt: Date.now(),
        }),
      clear: () => set(initialState),
    }),
    {
      name: "allure-bot-meeting",
    }
  )
)
