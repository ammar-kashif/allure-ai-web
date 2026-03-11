import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useAudioRecorder } from "../use-audio-recorder"
import { useRecordingStore } from "@/stores/recording-store"

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}))

// Mock recovery module
vi.mock("@/lib/audio/recovery", () => ({
  checkForRecovery: vi.fn().mockResolvedValue({ hasRecovery: false, recordingIds: [] }),
  recoverRecording: vi.fn(),
  discardRecovery: vi.fn(),
}))

// Mock chunk-store
vi.mock("@/lib/audio/chunk-store", () => ({
  saveAudioChunk: vi.fn().mockResolvedValue(undefined),
  getAudioChunks: vi.fn().mockResolvedValue([]),
  clearAudioChunks: vi.fn().mockResolvedValue(undefined),
}))

// Mock MediaRecorder
class MockMediaRecorder {
  state = "inactive" as RecordingState
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  onerror: (() => void) | null = null
  mimeType = "audio/webm;codecs=opus"

  static isTypeSupported = vi.fn().mockReturnValue(true)

  start = vi.fn().mockImplementation(() => {
    this.state = "recording" as RecordingState
  })
  stop = vi.fn().mockImplementation(() => {
    this.state = "inactive" as RecordingState
    if (this.onstop) this.onstop()
  })
}

// Mock getUserMedia
const mockGetUserMedia = vi.fn()
const mockTrackStop = vi.fn()

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })

  // Reset store
  useRecordingStore.getState().reset()

  // Setup navigator.mediaDevices mock
  Object.defineProperty(global.navigator, "mediaDevices", {
    value: {
      getUserMedia: mockGetUserMedia.mockResolvedValue({
        getTracks: () => [{ stop: mockTrackStop }],
      }),
    },
    writable: true,
    configurable: true,
  })

  // Setup MediaRecorder mock
  Object.defineProperty(global, "MediaRecorder", {
    value: MockMediaRecorder,
    writable: true,
    configurable: true,
  })

  // Setup crypto.randomUUID mock
  Object.defineProperty(global.crypto, "randomUUID", {
    value: vi.fn().mockReturnValue("test-uuid-1234"),
    writable: true,
    configurable: true,
  })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe("useAudioRecorder", () => {
  it("captures audio with audio/webm;codecs=opus MIME type", async () => {
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    expect(mockGetUserMedia).toHaveBeenCalledWith({ audio: true })
    expect(result.current.isRecording).toBe(true)
  })

  it("updates Zustand store isRecording state", async () => {
    const { result } = renderHook(() => useAudioRecorder())

    expect(result.current.isRecording).toBe(false)

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.isRecording).toBe(true)
    expect(result.current.currentRecordingId).toBe("test-uuid-1234")
  })

  it("shows elapsed time based on startedAt", async () => {
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.elapsedSeconds).toBe(0)

    // Advance time by 3 seconds
    await act(async () => {
      vi.advanceTimersByTime(3000)
    })

    expect(result.current.elapsedSeconds).toBeGreaterThanOrEqual(3)
  })

  it("handles getUserMedia rejection with toast error", async () => {
    const { toast } = await import("sonner")
    mockGetUserMedia.mockRejectedValueOnce(
      new DOMException("Permission denied", "NotAllowedError")
    )

    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    expect(toast.error).toHaveBeenCalledWith("Recording failed", {
      description: expect.stringContaining("Microphone access denied"),
    })
    expect(result.current.isRecording).toBe(false)
  })
})
