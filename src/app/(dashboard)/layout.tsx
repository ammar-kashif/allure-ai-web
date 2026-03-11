"use client"

import { Toaster } from "sonner"

import { Providers } from "@/components/providers"
import { RecordingFAB } from "@/components/recording/recording-fab"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Providers>
      <div className="relative min-h-screen">
        <header className="border-b bg-background">
          <div className="mx-auto flex h-14 max-w-7xl items-center px-6">
            <h1 className="text-lg font-semibold tracking-tight">Allure</h1>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>

        <RecordingFAB />
        <Toaster position="bottom-left" richColors closeButton />
      </div>
    </Providers>
  )
}
