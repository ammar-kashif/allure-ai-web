"use client"

import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "sonner"
import { Providers } from "@/components/providers"
import { AppSidebar } from "@/components/app-sidebar"
import { RecordingFAB } from "@/components/recording/recording-fab"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Providers>
      <TooltipProvider>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset className="h-svh">
            <header className="flex h-14 shrink-0 items-center gap-2 px-6 shadow-[var(--shadow-sm)]">
              <SidebarTrigger />
            </header>
            <main className="flex-1 overflow-y-auto px-6 py-8 animate-fade-in-up">{children}</main>
            <div id="player-portal" />
          </SidebarInset>
          <RecordingFAB />
          <Toaster position="bottom-left" richColors closeButton />
        </SidebarProvider>
      </TooltipProvider>
    </Providers>
  )
}
