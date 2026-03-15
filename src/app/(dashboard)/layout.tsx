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
          <SidebarInset>
            <header className="flex h-14 items-center gap-2 px-6 shadow-[var(--shadow-sm)]">
              <SidebarTrigger />
            </header>
            <main className="flex-1 px-6 py-8 animate-fade-in-up">{children}</main>
          </SidebarInset>
          <RecordingFAB />
          <Toaster position="bottom-left" richColors closeButton />
        </SidebarProvider>
      </TooltipProvider>
    </Providers>
  )
}
