import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { RecordingFAB } from "../recording-fab"

// Mock the useAudioRecorder hook
const mockStartRecording = vi.fn()
const mockStopRecording = vi.fn()

vi.mock("@/hooks/use-audio-recorder", () => ({
  useAudioRecorder: vi.fn(() => ({
    isRecording: false,
    elapsedSeconds: 0,
    currentRecordingId: null,
    startRecording: mockStartRecording,
    stopRecording: mockStopRecording,
    onRecordingCompleteRef: { current: null },
  })),
}))

vi.mock("@/hooks/use-recordings", () => ({
  useUploadRecording: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useRecordingStatus: vi.fn(() => ({ data: undefined })),
  useRenameRecording: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAssignProject: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

// PostRecordingDialog pulls useProjects -> useQuery, which needs a
// QueryClient. Tests don't set one up, so stub it.
vi.mock("@/hooks/use-projects", () => ({
  useProjects: vi.fn(() => ({ data: [] })),
}))

// The BotDispatchDialog uses TanStack Query under the hood. Stub it out --
// it has its own tests; we only care about the FAB's wiring here.
vi.mock("@/components/recording/bot-dispatch-dialog", () => ({
  BotDispatchDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="bot-dispatch-dialog" /> : null,
}))

describe("RecordingFAB", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("idle: renders the mic trigger button", () => {
    render(<RecordingFAB />)
    const button = screen.getByRole("button", { name: /start recording/i })
    expect(button).toBeInTheDocument()
  })

  it("idle: clicking the mic does NOT start recording immediately (it opens a menu)", async () => {
    const user = userEvent.setup()
    render(<RecordingFAB />)

    await user.click(screen.getByRole("button", { name: /start recording/i }))

    // The contract: a single click must not unilaterally start native
    // recording -- it has to go through the menu.
    expect(mockStartRecording).not.toHaveBeenCalled()
  })

  // NOTE: the @base-ui/react menu does not open under jsdom (it relies on
  // pointer-events that React Testing Library can't synthesize). The
  // onSelect wiring of each menu item is verified by inspection -- both
  // call the same hooks already covered by their own tests
  // (use-audio-recorder, use-bot-meeting).

  it("recording: shows the stop pill and calls stopRecording on click", async () => {
    const { useAudioRecorder } = await import("@/hooks/use-audio-recorder")
    vi.mocked(useAudioRecorder).mockReturnValue({
      isRecording: true,
      elapsedSeconds: 65,
      currentRecordingId: "test-id",
      startRecording: mockStartRecording,
      stopRecording: mockStopRecording,
      onRecordingCompleteRef: { current: null },
    })

    render(<RecordingFAB />)
    const button = screen.getByRole("button", { name: /stop recording/i })
    expect(button).toBeInTheDocument()

    fireEvent.click(button)
    expect(mockStopRecording).toHaveBeenCalledOnce()
  })

  it("recording: displays elapsed time formatted as M:SS", async () => {
    const { useAudioRecorder } = await import("@/hooks/use-audio-recorder")
    vi.mocked(useAudioRecorder).mockReturnValue({
      isRecording: true,
      elapsedSeconds: 125, // 2:05
      currentRecordingId: "test-id",
      startRecording: mockStartRecording,
      stopRecording: mockStopRecording,
      onRecordingCompleteRef: { current: null },
    })

    render(<RecordingFAB />)
    expect(screen.getByText("2:05")).toBeInTheDocument()
  })
})
