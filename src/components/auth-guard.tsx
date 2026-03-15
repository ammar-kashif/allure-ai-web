"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { Loader2 } from "lucide-react"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading, firstRun } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    if (firstRun) {
      router.replace("/register")
    } else if (!user) {
      router.replace("/login")
    }
  }, [isLoading, user, firstRun, router])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!user) return null

  return <>{children}</>
}
