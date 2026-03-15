import { Card, CardContent } from "@/components/ui/card"
import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  title: string
  value: number
  icon: LucideIcon
}

export function StatCard({ title, value, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className="rounded-xl bg-primary/8 p-3">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-[0.8125rem] font-medium text-muted-foreground">{title}</p>
          <p className="text-[1.75rem] font-heading font-semibold tracking-[-0.02em]">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}
