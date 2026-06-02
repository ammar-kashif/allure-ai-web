import { create } from "zustand"

export type TabId = "info" | "transcript" | "outcomes" | "prd" | "diagram"

interface EvidenceHighlightState {
  highlightUtteranceIndex: number | null
  activeTab: TabId
}

interface EvidenceHighlightActions {
  setHighlight: (index: number) => void
  clearHighlight: () => void
  setActiveTab: (tab: TabId) => void
}

let clearTimeoutId: ReturnType<typeof setTimeout> | null = null

export const useEvidenceHighlight = create<
  EvidenceHighlightState & EvidenceHighlightActions
>()((set) => ({
  highlightUtteranceIndex: null,
  activeTab: "info",

  setHighlight: (index: number) => {
    // Clear any existing auto-clear timer
    if (clearTimeoutId !== null) {
      clearTimeout(clearTimeoutId)
    }

    set({ highlightUtteranceIndex: index, activeTab: "transcript" })

    // Auto-clear highlight after 3 seconds
    clearTimeoutId = setTimeout(() => {
      set({ highlightUtteranceIndex: null })
      clearTimeoutId = null
    }, 3000)
  },

  clearHighlight: () => {
    if (clearTimeoutId !== null) {
      clearTimeout(clearTimeoutId)
      clearTimeoutId = null
    }
    set({ highlightUtteranceIndex: null })
  },

  setActiveTab: (tab: TabId) => set({ activeTab: tab }),
}))

