"use client"

import { Mic, Brain, CheckSquare } from "lucide-react"
import { useDashboardStats } from "@/hooks/use-dashboard-stats"
import { StatCard } from "@/components/dashboard/stat-card"
import { RecentRecordings } from "@/components/dashboard/recent-recordings"
import { RecentOutcomes } from "@/components/dashboard/recent-outcomes"
import { DashboardEmptyState } from "@/components/dashboard/empty-state"
import { Skeleton } from "@/components/ui/skeleton"

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const {
    totalRecordings,
    outcomesExtracted,
    tasksCreated,
    isLoading,
    recordings,
    allOutcomes,
  } = useDashboardStats()

  if (isLoading) {
    return <DashboardSkeleton />
  }

  if (totalRecordings === 0) {
    return <DashboardEmptyState />
  }

  return (
    <div className="space-y-8">
      <h1 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em] text-foreground">
        Dashboard
      </h1>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <div className="animate-stagger" style={{ "--stagger-index": 0 } as React.CSSProperties}>
          <StatCard title="Total Recordings" value={totalRecordings} icon={Mic} />
        </div>
        <div className="animate-stagger" style={{ "--stagger-index": 1 } as React.CSSProperties}>
          <StatCard title="Outcomes Extracted" value={outcomesExtracted} icon={Brain} />
        </div>
        <div className="animate-stagger" style={{ "--stagger-index": 2 } as React.CSSProperties}>
          <StatCard title="Tasks Created" value={tasksCreated} icon={CheckSquare} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="animate-stagger" style={{ "--stagger-index": 3 } as React.CSSProperties}>
          <RecentRecordings recordings={recordings} />
        </div>
        <div className="animate-stagger" style={{ "--stagger-index": 4 } as React.CSSProperties}>
          <RecentOutcomes outcomes={allOutcomes} />
        </div>
      </div>
    </div>
  )
}
