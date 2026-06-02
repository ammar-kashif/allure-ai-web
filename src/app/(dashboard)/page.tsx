"use client"

import { Mic, Brain, CheckSquare, FileText } from "lucide-react"
import { useDashboardStats } from "@/hooks/use-dashboard-stats"
import { StatCard } from "@/components/dashboard/stat-card"
import { RecentRecordings } from "@/components/dashboard/recent-recordings"
import { RecentOutcomes } from "@/components/dashboard/recent-outcomes"
import { DashboardEmptyState } from "@/components/dashboard/empty-state"
import { Skeleton } from "@/components/ui/skeleton"

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 border-y border-border/70 py-6 md:grid-cols-4 md:gap-0 md:divide-x md:divide-border/70">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2 md:px-8 md:first:pl-0 md:last:pr-0">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
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
    documentsGenerated,
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
      <h1 className="text-display text-foreground">Dashboard</h1>

      <div className="grid grid-cols-2 gap-x-8 gap-y-6 border-y border-border/70 py-6 md:grid-cols-4 md:divide-x md:divide-border/70 md:gap-0">
        <div className="animate-stagger md:px-8 md:first:pl-0" style={{ "--stagger-index": 0 } as React.CSSProperties}>
          <StatCard title="Recordings" value={totalRecordings} icon={Mic} />
        </div>
        <div className="animate-stagger md:px-8" style={{ "--stagger-index": 1 } as React.CSSProperties}>
          <StatCard title="Outcomes" value={outcomesExtracted} icon={Brain} />
        </div>
        <div className="animate-stagger md:px-8" style={{ "--stagger-index": 2 } as React.CSSProperties}>
          <StatCard title="Tasks" value={tasksCreated} icon={CheckSquare} />
        </div>
        <div className="animate-stagger md:px-8 md:last:pr-0" style={{ "--stagger-index": 3 } as React.CSSProperties}>
          <StatCard title="Documents" value={documentsGenerated} icon={FileText} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="animate-stagger" style={{ "--stagger-index": 4 } as React.CSSProperties}>
          <RecentRecordings recordings={recordings} />
        </div>
        <div className="animate-stagger" style={{ "--stagger-index": 5 } as React.CSSProperties}>
          <RecentOutcomes outcomes={allOutcomes} />
        </div>
      </div>
    </div>
  )
}

