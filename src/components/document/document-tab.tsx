"use client"

import { useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, FileText, ChevronDown, ChevronRight, Link2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface SlideInfo {
  index: number
  title: string
  content: string
  notes: string
}

interface DocMeta {
  doc_index: number
  filename: string
  type: string
  slide_count: number
}

interface SlideAlignment {
  slide_index: number
  segment_indices: number[]
  relevance_scores: number[]
  summary: string
}

interface DocumentTabProps {
  recordingId: string
  transcriptUtterances?: { speaker: string; text: string; startTime: number }[]
}

export function DocumentTab({ recordingId, transcriptUtterances = [] }: DocumentTabProps) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null)
  const [expandedSlides, setExpandedSlides] = useState<Set<number>>(new Set())
  const [showAlignment, setShowAlignment] = useState(false)

  const { data: docs = [], isLoading: docsLoading } = useQuery<DocMeta[]>({
    queryKey: ["documents", recordingId],
    queryFn: async () => {
      const res = await fetch(`/api/recordings/${recordingId}/documents`)
      if (!res.ok) return []
      return res.json()
    },
  })

  const { data: slides = [] } = useQuery<SlideInfo[]>({
    queryKey: ["document-slides", recordingId, selectedDoc],
    queryFn: async () => {
      const res = await fetch(`/api/recordings/${recordingId}/documents/${selectedDoc}`)
      if (!res.ok) return []
      const doc = await res.json()
      return doc.slides ?? []
    },
    enabled: selectedDoc !== null,
  })

  const { data: alignment, isFetching: alignmentLoading } = useQuery<{ alignments: SlideAlignment[] }>({
    queryKey: ["alignment", recordingId, selectedDoc],
    queryFn: async () => {
      const res = await fetch(`/api/recordings/${recordingId}/alignment/${selectedDoc}`)
      if (!res.ok) throw new Error("Alignment failed")
      return res.json()
    },
    enabled: selectedDoc !== null && showAlignment,
  })

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append("file", file)
      const res = await fetch(`/api/recordings/${recordingId}/documents`, {
        method: "POST",
        body: form,
      })
      if (!res.ok) throw new Error("Upload failed")
      return res.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["documents", recordingId] })
      setSelectedDoc(data.doc_index)
      toast.success(`Document uploaded: ${data.filename} (${data.slide_count} slides)`)
    },
    onError: () => toast.error("Document upload failed"),
  })

  const alignmentBySlide = new Map(
    (alignment?.alignments ?? []).map((a) => [a.slide_index, a])
  )

  function toggleSlide(index: number) {
    setExpandedSlides((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  return (
    <div className="space-y-6">
      {/* Upload area */}
      <div
        className={cn(
          "rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-colors",
          uploadMutation.isPending ? "opacity-60 pointer-events-none" : "hover:border-primary/50"
        )}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.pptx,.ppt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) uploadMutation.mutate(file)
          }}
        />
        {uploadMutation.isPending ? (
          <div className="flex items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Uploading and parsing…
          </div>
        ) : (
          <>
            <Upload className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-sm font-medium">Click to upload PDF or PPTX</p>
            <p className="text-xs text-muted-foreground mt-0.5">Slides will be parsed and can be aligned with the transcript</p>
          </>
        )}
      </div>

      {/* Document list */}
      {!docsLoading && docs.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Uploaded documents</h3>
          <div className="flex flex-wrap gap-2">
            {docs.map((doc) => (
              <button
                key={doc.doc_index}
                onClick={() => { setSelectedDoc(doc.doc_index); setShowAlignment(false) }}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors",
                  selectedDoc === doc.doc_index
                    ? "border-primary bg-primary/5 text-primary"
                    : "hover:bg-muted/50"
                )}
              >
                <FileText className="h-4 w-4" />
                <span className="truncate max-w-[160px]">{doc.filename}</span>
                <span className="text-xs text-muted-foreground">{doc.slide_count} slides</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Slides viewer */}
      {selectedDoc !== null && slides.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">{slides.length} slides</h3>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setShowAlignment((v) => !v)}
              disabled={transcriptUtterances.length === 0}
            >
              {alignmentLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Link2 className="h-3.5 w-3.5" />
              )}
              {showAlignment ? "Hide alignment" : "Show transcript alignment"}
            </Button>
          </div>

          <div className="space-y-2">
            {slides.map((slide) => {
              const expanded = expandedSlides.has(slide.index)
              const slideAlignment = alignmentBySlide.get(slide.index)

              return (
                <div key={slide.index} className="rounded-lg border overflow-hidden">
                  <button
                    className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-muted/30 transition-colors"
                    onClick={() => toggleSlide(slide.index)}
                  >
                    {expanded ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
                    <span className="text-xs text-muted-foreground w-8 shrink-0">{slide.index + 1}</span>
                    <span className="font-medium text-sm truncate">{slide.title}</span>
                  </button>

                  {expanded && (
                    <div className="px-4 pb-4 space-y-3 border-t bg-muted/10">
                      {slide.content && (
                        <div className="pt-3">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Content</p>
                          <p className="text-sm whitespace-pre-wrap">{slide.content}</p>
                        </div>
                      )}
                      {slide.notes && (
                        <div>
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Speaker notes</p>
                          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{slide.notes}</p>
                        </div>
                      )}

                      {showAlignment && slideAlignment && (
                        <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 space-y-2">
                          <p className="text-xs font-semibold text-primary">Transcript alignment</p>
                          <p className="text-xs text-muted-foreground">{slideAlignment.summary}</p>
                          {slideAlignment.segment_indices.length > 0 && (
                            <div className="space-y-1.5 mt-2">
                              {slideAlignment.segment_indices.map((segIdx, i) => {
                                const utt = transcriptUtterances[segIdx]
                                const score = slideAlignment.relevance_scores[i] ?? 0
                                return utt ? (
                                  <div key={segIdx} className="flex gap-2 text-xs">
                                    <div
                                      className="shrink-0 h-4 w-1 rounded-full bg-primary/60"
                                      style={{ opacity: score }}
                                    />
                                    <div>
                                      <span className="font-medium">{utt.speaker}</span>
                                      <span className="text-muted-foreground ml-1">({Math.round(score * 100)}%)</span>
                                      <p className="text-muted-foreground mt-0.5 line-clamp-2">{utt.text}</p>
                                    </div>
                                  </div>
                                ) : null
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
