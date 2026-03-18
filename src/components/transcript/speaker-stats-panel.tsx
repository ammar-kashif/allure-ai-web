"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { SpeakerBadge } from "./speaker-badge"
import { InlineEdit } from "./inline-edit"
import { formatDuration } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { useUpdateSpeaker } from "@/hooks/use-recordings"
import type { SpeakerStat } from "@/types/recording"

interface SpeakerStatsPanelProps {
  speakers: SpeakerStat[]
  recordingId: string
}

export function SpeakerStatsPanel({ speakers, recordingId }: SpeakerStatsPanelProps) {
  const [open, setOpen] = useState(true)

  return (
    <Collapsible defaultOpen open={open} onOpenChange={setOpen}>
      <div className="rounded-xl bg-card shadow-[var(--shadow-card)]">
        <CollapsibleTrigger className="flex w-full items-center justify-between px-5 py-4">
          <h3 className="font-heading font-semibold tracking-[-0.01em]">
            Speaker Statistics
          </h3>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform duration-200",
              open && "rotate-180"
            )}
          />
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="space-y-3 px-5 pb-5">
            {speakers.map((speaker) => (
              <SpeakerRow key={speaker.label} stat={speaker} recordingId={recordingId} />
            ))}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function SpeakerRow({ stat, recordingId }: { stat: SpeakerStat; recordingId: string }) {
  const updateSpeaker = useUpdateSpeaker()

  return (
    <div className="rounded-lg border p-3">
      <div className="mb-2 flex items-center gap-3">
        <SpeakerBadge speaker={stat.label} displayName={stat.customLabel || stat.label} />
        <div className="flex flex-col gap-0.5">
          <InlineEdit
            value={stat.customLabel || stat.label}
            onSave={(newValue) =>
              updateSpeaker.mutate({
                recordingId,
                speakerLabel: stat.label,
                customLabel: newValue,
              })
            }
            className="text-sm font-medium"
            inputClassName="text-sm font-medium"
          />
          <InlineEdit
            value={stat.role || "Participant"}
            onSave={(newValue) =>
              updateSpeaker.mutate({
                recordingId,
                speakerLabel: stat.label,
                role: newValue,
              })
            }
            className="text-xs text-muted-foreground"
            inputClassName="text-xs"
            placeholder="Role"
          />
        </div>
        <span className="ml-auto text-sm font-medium text-muted-foreground">
          {stat.talkTimePct.toFixed(0)}% talk time
        </span>
      </div>
      <div className="grid grid-cols-4 gap-x-4 gap-y-2 text-sm">
        <MetricCell label="Talk Time" value={formatDuration(stat.talkTime * 1000)} />
        <MetricCell label="Words" value={String(stat.wordCount)} />
        <MetricCell label="WPM" value={stat.wpm.toFixed(1)} />
        <MetricCell label="Turns" value={String(stat.turns)} />
        <MetricCell label="Avg Turn" value={formatDuration(stat.avgTurnDuration * 1000)} />
        <MetricCell label="Pauses" value={String(stat.pauses)} />
        <MetricCell label="Avg Pause" value={formatDuration(stat.avgPauseDuration * 1000)} />
        <MetricCell label="Utterances" value={String(stat.utteranceCount)} />
      </div>
    </div>
  )
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-heading font-semibold tabular-nums">{value}</p>
    </div>
  )
}
