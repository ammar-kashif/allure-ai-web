import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
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
}))

describe("RecordingFAB", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders mic icon when not recording", () => {
    render(<RecordingFAB />)
    const button = screen.getByRole("button", { name: /start recording/i })
    expect(button).toBeInTheDocument()
  })

  it("start recording - calls startRecording on click", () => {
    render(<RecordingFAB />)
    const button = screen.getByRole("button", { name: /start recording/i })

    fireEvent.click(button)
    expect(mockStartRecording).toHaveBeenCalledOnce()
  })

  it("stop recording - shows stop button when recording", async () => {
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
  })

  it("displays elapsed time formatted as M:SS", async () => {
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

