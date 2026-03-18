"use client"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const SPEED_OPTIONS = [0.5, 1, 1.5, 2] as const

interface SpeedSelectorProps {
  value: number
  onChange: (rate: number) => void
}

export function SpeedSelector({ value, onChange }: SpeedSelectorProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs font-semibold tabular-nums" />
        }
      >
        {value}x
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" side="top" sideOffset={8}>
        {SPEED_OPTIONS.map((speed) => (
          <DropdownMenuItem
            key={speed}
            onClick={() => onChange(speed)}
            className={speed === value ? "font-semibold" : ""}
          >
            {speed}x
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
