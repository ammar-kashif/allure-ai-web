import { create } from "zustand"

interface AudioPlaybackState {
  isPlaying: boolean
  currentTime: number
  duration: number
  playbackRate: number
  activeUtteranceIndex: number | null
  autoScrollEnabled: boolean
}

interface AudioPlaybackActions {
  play: () => void
  pause: () => void
  togglePlayback: () => void
  seek: (time: number) => void
  setPlaybackRate: (rate: number) => void
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setActiveUtterance: (index: number | null) => void
  disableAutoScroll: () => void
  enableAutoScroll: () => void
  reset: () => void
}

const initialState: AudioPlaybackState = {
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  playbackRate: 1,
  activeUtteranceIndex: null,
  autoScrollEnabled: true,
}

export const useAudioPlayback = create<
  AudioPlaybackState & AudioPlaybackActions
>()((set) => ({
  ...initialState,

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  togglePlayback: () => set((state) => ({ isPlaying: !state.isPlaying })),
  seek: (time: number) => set({ currentTime: time }),
  setPlaybackRate: (rate: number) => set({ playbackRate: rate }),
  setCurrentTime: (time: number) => set({ currentTime: time }),
  setDuration: (duration: number) => set({ duration }),
  setActiveUtterance: (index: number | null) =>
    set({ activeUtteranceIndex: index }),
  disableAutoScroll: () => set({ autoScrollEnabled: false }),
  enableAutoScroll: () => set({ autoScrollEnabled: true }),
  reset: () => set(initialState),
}))
