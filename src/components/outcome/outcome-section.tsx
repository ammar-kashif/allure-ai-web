"use client"

import { useState } from "react"
import {
  FileText,
  CheckSquare,
  Target,
  AlertTriangle,
  ChevronDown,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { OutcomeType } from "@/types/outcome"
import { cn } from "@/lib/utils"

const typeConfig: Record<
  OutcomeType,
  { icon: React.ElementType; label: string }
> = {
  decision: { icon: FileText, label: "Decisions" },
  action_item: { icon: CheckSquare, label: "Action Items" },
  requirement: { icon: Target, label: "Requirements" },
  blocker: { icon: AlertTriangle, label: "Blockers" },
}

interface OutcomeSectionProps {
  type: OutcomeType
  count: number
  children: React.ReactNode
}

export function OutcomeSection({ type, count, children }: OutcomeSectionProps) {
  const [open, setOpen] = useState(true)
  const { icon: Icon, label } = typeConfig[type]

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-muted/60 transition-colors"
      >
        <Icon className="size-4 text-muted-foreground" />
        <span className="font-medium">{label}</span>
        <Badge variant="secondary" className="ml-1">
          {count}
        </Badge>
        <ChevronDown
          className={cn(
            "ml-auto size-4 text-muted-foreground transition-transform",
            open && "rotate-180"
          )}
        />
      </button>
      {open && <div className="space-y-2 pl-2">{children}</div>}
    </div>
  )
}
