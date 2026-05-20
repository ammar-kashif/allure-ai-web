"use client"

import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

import type { GhostCitation } from "./types"

function formatTimestamp(seconds?: number) {
  if (typeof seconds !== "number") return ""
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function GhostCitationPill({ cite }: { cite: GhostCitation }) {
  if (cite.source_type === "segment" && cite.recording_id) {
    const ts = formatTimestamp(cite.timestamp)
    const label = ts ? `${ts}${cite.speaker ? ` · ${cite.speaker}` : ""}` : (cite.speaker ?? "transcript")
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <Link
              href={`/recordings/${cite.recording_id}#segment-${cite.segment_index ?? 0}`}
              className="inline-flex"
            >
              <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                {label}
              </Badge>
            </Link>
          }
        />
        <TooltipContent>
          <p className="max-w-xs text-xs">{cite.text}</p>
        </TooltipContent>
      </Tooltip>
    )
  }
  if (cite.source_type === "attachment" && cite.recording_id) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <Link
              href={`/recordings/${cite.recording_id}#attachment-${cite.attachment_id}`}
              className="inline-flex"
            >
              <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                {cite.filename ?? "document"}
              </Badge>
            </Link>
          }
        />
        <TooltipContent>
          <p className="max-w-xs text-xs">{cite.snippet}</p>
        </TooltipContent>
      </Tooltip>
    )
  }
  if (cite.source_type === "outcome" && cite.recording_id) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <Link
              href={`/recordings/${cite.recording_id}#outcomes`}
              className="inline-flex"
            >
              <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                {cite.type ?? "outcome"}: {cite.title ?? "—"}
              </Badge>
            </Link>
          }
        />
        <TooltipContent>
          <p className="max-w-xs text-xs">{cite.detail}</p>
        </TooltipContent>
      </Tooltip>
    )
  }
  return null
}
