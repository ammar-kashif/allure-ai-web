"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Pencil } from "lucide-react"

interface InlineEditProps {
  value: string
  onSave: (newValue: string) => void
  className?: string
  inputClassName?: string
  placeholder?: string
}

export function InlineEdit({
  value,
  onSave,
  className,
  inputClassName,
  placeholder,
}: InlineEditProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)

  // Sync draft when value prop changes externally
  useEffect(() => {
    if (!editing) {
      setDraft(value)
    }
  }, [value, editing])

  // Auto-focus input when entering edit mode
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  const handleSave = useCallback(() => {
    const trimmed = draft.trim()
    if (!trimmed || trimmed === value) {
      // Revert if empty or unchanged
      setDraft(value)
    } else {
      onSave(trimmed)
    }
    setEditing(false)
  }, [draft, value, onSave])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault()
        handleSave()
      } else if (e.key === "Escape") {
        e.preventDefault()
        setDraft(value)
        setEditing(false)
      }
    },
    [handleSave, value]
  )

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={`rounded border px-1.5 py-0.5 text-sm outline-none focus:ring-2 focus:ring-ring ${inputClassName ?? ""}`}
      />
    )
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className={`inline-flex items-center gap-1 ${className ?? ""}`}
    >
      <span>{value}</span>
      <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
    </button>
  )
}

