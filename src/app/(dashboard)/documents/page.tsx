"use client"

import { useMemo } from "react"
import Link from "next/link"
import { FileText } from "lucide-react"

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { DocumentTypeBadge } from "@/components/document/document-type-badge"
import { useDocuments } from "@/hooks/use-documents"
import { useRecordings } from "@/hooks/use-recordings"
import type { Document } from "@/lib/db/documents"
import type { Recording } from "@/types/recording"

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function DocumentsTable({ documents, recordingsMap }: { documents: Document[]; recordingsMap: Map<string, Recording> }) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-12 text-center">
        <FileText className="h-10 w-10 text-muted-foreground/50" />
        <p className="text-base text-muted-foreground">
          No documents generated yet.
        </p>
        <p className="text-sm text-muted-foreground/80">
          Generate a PRD or diagram from a recording.
        </p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Source Recording</TableHead>
          <TableHead>Date Generated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((doc) => (
          <TableRow key={doc.id}>
            <TableCell>
              <Link
                href={`/documents/${doc.id}`}
                className="font-medium text-foreground hover:text-primary transition-colors duration-[var(--duration-fast)]"
              >
                {doc.title}
              </Link>
            </TableCell>
            <TableCell>
              <DocumentTypeBadge type={doc.type} />
            </TableCell>
            <TableCell className="text-muted-foreground">
              {recordingsMap.get(doc.sourceRecordingId)?.title ?? doc.sourceRecordingId}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatDate(doc.createdAt)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default function DocumentsPage() {
  const { data: allDocuments = [], isLoading } = useDocuments()
  const { data: prdDocuments = [] } = useDocuments("prd")
  const { data: recordings = [] } = useRecordings()

  const recordingsMap = useMemo(
    () => new Map(recordings.map((r) => [r.id, r])),
    [recordings]
  )

  const diagramDocuments = useMemo(
    () => allDocuments.filter((d) => d.type === "user_flow" || d.type === "erd"),
    [allDocuments]
  )

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-2 h-5 w-72" />
        </div>
        <Skeleton className="h-8 w-64" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[1.75rem] font-heading font-bold tracking-[-0.02em]">
          Documents
        </h1>
        <p className="mt-1 text-[0.9375rem] text-muted-foreground">
          Generated PRDs and diagrams from your recordings.
        </p>
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">
            All
            <span className="ml-1 text-xs text-muted-foreground">
              ({allDocuments.length})
            </span>
          </TabsTrigger>
          <TabsTrigger value="prds">
            PRDs
            <span className="ml-1 text-xs text-muted-foreground">
              ({prdDocuments.length})
            </span>
          </TabsTrigger>
          <TabsTrigger value="diagrams">
            Diagrams
            <span className="ml-1 text-xs text-muted-foreground">
              ({diagramDocuments.length})
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <DocumentsTable documents={allDocuments} recordingsMap={recordingsMap} />
        </TabsContent>
        <TabsContent value="prds">
          <DocumentsTable documents={prdDocuments} recordingsMap={recordingsMap} />
        </TabsContent>
        <TabsContent value="diagrams">
          <DocumentsTable documents={diagramDocuments} recordingsMap={recordingsMap} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
