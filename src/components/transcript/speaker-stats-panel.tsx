"use client"

import { useCallback, useRef, useState } from "react"
import { Pencil, Check, X } from "lucide-react"

import { cn } from "@/lib/utils"
import type { SpeakerStats } from "@/types/recording"

// Must stay in sync with utterance-bubble.tsx
const speakerColors = [
  { bg: "bg-indigo-100", bar: "bg-indigo-400", label: "text-indigo-700", border: "border-indigo-200" },
  { bg: "bg-teal-100", bar: "bg-teal-400", label: "text-teal-700", border: "border-teal-200" },
  { bg: "bg-violet-100", bar: "bg-violet-400", label: "text-violet-700", border: "border-violet-200" },
  { bg: "bg-amber-100", bar: "bg-amber-400", label: "text-amber-700", border: "border-amber-200" },
  { bg: "bg-rose-100", bar: "bg-rose-400", label: "text-rose-700", border: "border-rose-200" },
] as const

function getSpeakerColorIndex(label: string): number {
  const match = label.match(/(\d+)/)
  if (match) {
    return (parseInt(match[1], 10) - 1) % speakerColors.length
  }
  return 0
}

interface SpeakerCardProps {
  speaker: SpeakerStats
  colorIndex: number
  isDominant: boolean
  onRename: (oldLabel: string, newLabel: string) => void
  onRoleChange: (label: string, newRole: string) => void
}

function SpeakerCard({ speaker, colorIndex, isDominant, onRename, onRoleChange }: SpeakerCardProps) {
  const colors = speakerColors[colorIndex]

  // Name editing
  const [isEditingName, setIsEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState(speaker.label)
  const nameInputRef = useRef<HTMLInputElement>(null)

  // Role editing
  const [isEditingRole, setIsEditingRole] = useState(false)
  const [roleDraft, setRoleDraft] = useState(speaker.role ?? "")
  const roleInputRef = useRef<HTMLInputElement>(null)

  const startEditName = useCallback(() => {
    setNameDraft(speaker.label)
    setIsEditingName(true)
    setTimeout(() => {
      nameInputRef.current?.focus()
      nameInputRef.current?.select()
    }, 0)
  }, [speaker.label])

  const confirmName = useCallback(() => {
    const trimmed = nameDraft.trim()
    if (trimmed && trimmed !== speaker.label) {
      onRename(speaker.label, trimmed)
    }
    setIsEditingName(false)
  }, [nameDraft, speaker.label, onRename])

  const cancelName = useCallback(() => {
    setNameDraft(speaker.label)
    setIsEditingName(false)
  }, [speaker.label])

  const startEditRole = useCallback(() => {
    setRoleDraft(speaker.role ?? "")
    setIsEditingRole(true)
    setTimeout(() => {
      roleInputRef.current?.focus()
      roleInputRef.current?.select()
    }, 0)
  }, [speaker.role])

  const confirmRole = useCallback(() => {
    const trimmed = roleDraft.trim()
    if (trimmed !== (speaker.role ?? "")) {
      onRoleChange(speaker.label, trimmed)
    }
    setIsEditingRole(false)
  }, [roleDraft, speaker.role, speaker.label, onRoleChange])

  const cancelRole = useCallback(() => {
    setRoleDraft(speaker.role ?? "")
    setIsEditingRole(false)
  }, [speaker.role])

  return (
    <div
      className={cn(
        "rounded-xl border p-3 space-y-2",
        colors.bg,
        colors.border
      )}
    >
      {/* Speaker name row */}
      <div className="flex items-center gap-2">
        {isEditingName ? (
          <>
            <input
              ref={nameInputRef}
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") confirmName()
                if (e.key === "Escape") cancelName()
              }}
              className={cn(
                "min-w-0 flex-1 rounded border bg-white/80 px-2 py-0.5 text-sm font-semibold outline-none",
                colors.label
              )}
            />
            <button
              onClick={confirmName}
              className="shrink-0 rounded p-0.5 hover:bg-white/50"
              aria-label="Confirm rename"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={cancelName}
              className="shrink-0 rounded p-0.5 hover:bg-white/50"
              aria-label="Cancel rename"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </>
        ) : (
          <>
            <span className={cn("min-w-0 flex-1 truncate text-sm font-semibold", colors.label)}>
              {speaker.label}
            </span>
            {isDominant && (
              <span className="shrink-0 rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Dominant
              </span>
            )}
            <button
              onClick={startEditName}
              className="shrink-0 rounded p-0.5 opacity-0 transition-opacity hover:bg-white/50 group-hover/card:opacity-100"
              aria-label={`Rename ${speaker.label}`}
            >
              <Pencil className="h-3 w-3" />
            </button>
          </>
        )}
      </div>

      {/* Role row */}
      <div className="flex items-center gap-1.5 min-h-[1.25rem]">
        {isEditingRole ? (
          <>
            <input
              ref={roleInputRef}
              value={roleDraft}
              onChange={(e) => setRoleDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") confirmRole()
                if (e.key === "Escape") cancelRole()
              }}
              placeholder="Enter role..."
              className="min-w-0 flex-1 rounded border bg-white/80 px-2 py-0.5 text-xs outline-none text-muted-foreground"
            />
            <button
              onClick={confirmRole}
              className="shrink-0 rounded p-0.5 hover:bg-white/50"
              aria-label="Confirm role"
            >
              <Check className="h-3 w-3" />
            </button>
            <button
              onClick={cancelRole}
              className="shrink-0 rounded p-0.5 hover:bg-white/50"
              aria-label="Cancel role edit"
            >
              <X className="h-3 w-3" />
            </button>
          </>
        ) : (
          <>
            {speaker.role ? (
              <span className="rounded-full bg-white/60 px-2 py-0.5 text-[11px] text-muted-foreground font-medium truncate">
                {speaker.role}
              </span>
            ) : (
              <span className="text-[11px] text-muted-foreground/50 italic">No role assigned</span>
            )}
            <button
              onClick={startEditRole}
              className="shrink-0 rounded p-0.5 opacity-0 transition-opacity hover:bg-white/50 group-hover/card:opacity-100"
              aria-label={`Edit role for ${speaker.label}`}
            >
              <Pencil className="h-2.5 w-2.5 text-muted-foreground" />
            </button>
          </>
        )}
      </div>

      {/* Talk time bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/50">
        <div
          className={cn("h-full rounded-full", colors.bar)}
          style={{ width: `${speaker.talkTimePct}%` }}
        />
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{speaker.talkTimePct.toFixed(1)}% talk time</span>
        <span>{speaker.utteranceCount} utterance{speaker.utteranceCount !== 1 ? "s" : ""}</span>
      </div>
    </div>
  )
}

interface SpeakerStatsPanelProps {
  speakers: SpeakerStats[]
  onRename: (oldLabel: string, newLabel: string) => void
  onRoleChange: (label: string, newRole: string) => void
}

export function SpeakerStatsPanel({ speakers, onRename, onRoleChange }: SpeakerStatsPanelProps) {
  if (!speakers || speakers.length === 0) return null

  const dominantLabel = speakers.reduce(
    (max, s) => (s.talkTimePct > max.talkTimePct ? s : max),
    speakers[0]
  ).label

  return (
    <div className="rounded-xl border bg-card p-4 shadow-[var(--shadow-card)] space-y-3">
      <h3 className="font-heading text-sm font-semibold tracking-[-0.01em]">
        Speakers
      </h3>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {speakers.map((speaker) => {
          const colorIndex = getSpeakerColorIndex(speaker.label)
          return (
            <div key={speaker.label} className="group/card">
              <SpeakerCard
                speaker={speaker}
                colorIndex={colorIndex}
                isDominant={speaker.label === dominantLabel}
                onRename={onRename}
                onRoleChange={onRoleChange}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
