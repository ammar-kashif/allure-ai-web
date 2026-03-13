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
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold tracking-tight">
        Dashboard
      </h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard title="Total Recordings" value={totalRecordings} icon={Mic} />
        <StatCard
          title="Outcomes Extracted"
          value={outcomesExtracted}
          icon={Brain}
        />
        <StatCard
          title="Tasks Created"
          value={tasksCreated}
          icon={CheckSquare}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentRecordings recordings={recordings} />
        <RecentOutcomes outcomes={allOutcomes} />
      </div>
    </div>
  )
}
