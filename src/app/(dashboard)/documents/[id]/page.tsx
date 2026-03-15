"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { DocumentTypeBadge } from "@/components/document/document-type-badge"
import { MermaidDiagram } from "@/components/document/mermaid-diagram"
import { useDocument } from "@/hooks/use-documents"
import { cn } from "@/lib/utils"

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

function PrdContent({ content }: { content: string }) {
  const lines = content.split("\n")

  return (
    <div className="rounded-xl bg-card p-6 shadow-[var(--shadow-card)] space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim()

        // Markdown-style headers (## or **)
        if (trimmed.startsWith("## ") || trimmed.startsWith("**") && trimmed.endsWith("**")) {
          const text = trimmed.replace(/^##\s*/, "").replace(/^\*\*|\*\*$/g, "")
          return (
            <h3
              key={i}
              className="font-heading font-semibold text-lg pt-4 first:pt-0"
            >
              {text}
            </h3>
          )
        }

        // Empty lines
        if (trimmed === "") {
          return <div key={i} className="h-2" />
        }

        // Regular text / bullets
        return (
          <p key={i} className="text-base leading-relaxed text-foreground/90">
            {line}
          </p>
        )
      })}
    </div>
  )
}

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const { data: document, isLoading, error } = useDocument(id)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-24" />
        <div className="space-y-2">
          <Skeleton className="h-8 w-96" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="space-y-6">
        <Link
          href="/documents"
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-2")}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Documents
        </Link>
        <div className="py-12 text-center">
          <h2 className="text-xl font-semibold">Document not found</h2>
          <p className="mt-2 text-muted-foreground">
            The document you are looking for does not exist or has been removed.
          </p>
          <Link
            href="/documents"
            className={cn(buttonVariants({ variant: "outline" }), "mt-4 inline-flex")}
          >
            Back to Documents
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <Link
        href="/documents"
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-2")}
      >
        <ArrowLeft className="mr-1 h-4 w-4" />
        Documents
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em]">
            {document.title}
          </h2>
          <DocumentTypeBadge type={document.type} />
        </div>
        <p className="text-[0.8125rem] text-muted-foreground">
          Generated on {formatDate(document.createdAt)}
        </p>
      </div>

      {/* Content */}
      {document.type === "prd" ? (
        <PrdContent content={document.content} />
      ) : (
        <div className="rounded-xl bg-card p-6 shadow-[var(--shadow-card)]">
          <MermaidDiagram code={document.content} />
        </div>
      )}
    </div>
  )
}
