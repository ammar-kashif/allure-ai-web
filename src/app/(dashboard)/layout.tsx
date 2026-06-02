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
            <header
              className="flex h-12 shrink-0 items-center gap-2 border-b border-border/60"
              style={{ paddingInline: "clamp(1rem, 2.5vw, 2rem)" }}
            >
              <SidebarTrigger />
            </header>
            <main
              className="flex-1 overflow-y-auto animate-fade-in-up"
              style={{
                paddingInline: "clamp(1rem, 2.5vw, 2rem)",
                paddingBlock: "clamp(1.5rem, 3vw, 2.5rem)",
              }}
            >
              <div className="mx-auto w-full max-w-[1400px]">{children}</div>
            </main>
            <div id="player-portal" />
          </SidebarInset>
          <RecordingFAB />
          <Toaster position="bottom-left" richColors closeButton />
        </SidebarProvider>
      </TooltipProvider>
    </Providers>
  )
}

