import { clsx, type ClassValue } from "clsx"
import { format } from "date-fns"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Generate a recording title from the current date/time.
 * Format: "Recording Mar 12, 2026 3:45 PM"
 */
export function generateRecordingTitle(date: Date = new Date()): string {
  return `Recording ${format(date, "MMM d, yyyy h:mm a")}`
}

/**
 * Format a duration in milliseconds to a human-readable string.
 * e.g. 65000 -> "1:05", 3600000 -> "1:00:00"
 */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

/**
 * Format an ISO timestamp to a readable date string.
 * e.g. "2026-03-12T15:45:00Z" -> "Mar 12, 2026"
 */
export function formatTimestamp(isoString: string): string {
  return format(new Date(isoString), "MMM d, yyyy")
}
