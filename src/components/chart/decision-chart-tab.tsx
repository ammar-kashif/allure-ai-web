"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronUp, Copy, Download, Loader2, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDecisionChart, useGenerateChart } from "@/hooks/use-outcomes"

// PlantUML uses a custom base64 table
const PLANTUML_CHARS =
  "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

function plantumlBase64Encode(data: Uint8Array): string {
  let result = ""
  for (let i = 0; i < data.length; i += 3) {
    const b0 = data[i]
    const b1 = i + 1 < data.length ? data[i + 1] : 0
    const b2 = i + 2 < data.length ? data[i + 2] : 0
    result += PLANTUML_CHARS[(b0 >> 2) & 0x3f]
    result += PLANTUML_CHARS[((b0 & 0x3) << 4) | ((b1 >> 4) & 0xf)]
    result += PLANTUML_CHARS[((b1 & 0xf) << 2) | ((b2 >> 6) & 0x3)]
    result += PLANTUML_CHARS[b2 & 0x3f]
  }
  return result
}

async function encodePlantuml(src: string): Promise<string> {
  const input = new TextEncoder().encode(src)
  const cs = new CompressionStream("deflate-raw")
  const writer = cs.writable.getWriter()
  writer.write(input)
  writer.close()
  const chunks: Uint8Array[] = []
  const reader = cs.readable.getReader()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  const totalLength = chunks.reduce((acc, c) => acc + c.length, 0)
  const compressed = new Uint8Array(totalLength)
  let offset = 0
  for (const chunk of chunks) {
    compressed.set(chunk, offset)
    offset += chunk.length
  }
  return plantumlBase64Encode(compressed)
}

interface DecisionChartTabProps {
  recordingId: string
}

export function DecisionChartTab({ recordingId }: DecisionChartTabProps) {
  const { data, isLoading } = useDecisionChart(recordingId, true)
  const generateMutation = useGenerateChart(recordingId)
  const [showSource, setShowSource] = useState(false)
  const [copied, setCopied] = useState(false)
  const [svgUrl, setSvgUrl] = useState<string | null>(null)

  const chartStatus = data?.chartStatus ?? "none"
  const plantuml = data?.chartPlantuml ?? null

  const serverUrl =
    process.env.NEXT_PUBLIC_PLANTUML_SERVER_URL ||
    "https://www.plantuml.com/plantuml"

  // Encode PlantUML asynchronously when content is available
  const encodingRef = useRef<string | null>(null)
  useEffect(() => {
    if (!plantuml) {
      setSvgUrl(null)
      return
    }
    if (encodingRef.current === plantuml) return
    encodingRef.current = plantuml
    encodePlantuml(plantuml).then((encoded) => {
      setSvgUrl(`${serverUrl}/svg/${encoded}`)
    })
  }, [plantuml, serverUrl])

  const handleGenerate = useCallback(() => {
    generateMutation.mutate()
  }, [generateMutation])

  const handleCopy = useCallback(async () => {
    if (!plantuml) return
    await navigator.clipboard.writeText(plantuml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [plantuml])

  const handleDownloadSvg = useCallback(() => {
    if (!svgUrl) return
    window.open(svgUrl, "_blank", "noopener,noreferrer")
  }, [svgUrl])

  // Loading initial query
  if (isLoading) {
    return <ChartSkeleton />
  }

  // Not started
  if (chartStatus === "none") {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <div className="space-y-1">
          <p className="font-medium">No decision chart yet</p>
          <p className="text-sm text-muted-foreground">
            Generate a PlantUML activity diagram that maps decisions from this
            meeting with speaker attribution and rationale.
          </p>
        </div>
        <Button
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
          size="sm"
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              Triggering...
            </>
          ) : (
            "Generate Decision Chart"
          )}
        </Button>
      </div>
    )
  }

  // In-progress
  if (chartStatus === "pending" || chartStatus === "processing") {
    return (
      <div className="flex flex-col items-center gap-3 py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          {chartStatus === "pending"
            ? "Chart generation queued..."
            : "Generating decision chart..."}
        </p>
      </div>
    )
  }

  // Failed
  if (chartStatus === "failed") {
    return (
      <div className="space-y-3 py-4">
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="font-medium text-destructive">Chart Generation Failed</p>
          <p className="mt-1 text-sm text-destructive/80">
            The LLM was unable to produce a valid chart for this recording.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
        >
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    )
  }

  // Completed
  return (
    <div className="space-y-4 pt-2">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <h3 className="font-heading text-sm font-semibold tracking-[-0.01em]">
          Decision Chart
        </h3>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSource((s) => !s)}
            className="gap-1.5 text-xs"
          >
            {showSource ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                Hide Source
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                View Source
              </>
            )}
          </Button>
          {plantuml && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="gap-1.5 text-xs"
            >
              <Copy className="h-3.5 w-3.5" />
              {copied ? "Copied!" : "Copy"}
            </Button>
          )}
          {svgUrl && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownloadSvg}
              className="gap-1.5 text-xs"
            >
              <Download className="h-3.5 w-3.5" />
              Open SVG
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${generateMutation.isPending ? "animate-spin" : ""}`} />
            {generateMutation.isPending ? "Regenerating..." : "Regenerate"}
          </Button>
        </div>
      </div>

      {/* PlantUML source */}
      {showSource && plantuml && (
        <pre className="overflow-x-auto rounded-xl border bg-muted/40 p-4 text-xs leading-relaxed">
          {plantuml}
        </pre>
      )}

      {/* Rendered diagram */}
      {svgUrl ? (
        <div className="overflow-auto rounded-xl border bg-white p-6 shadow-[var(--shadow-card)]">
          <DiagramImage svgUrl={svgUrl} plantuml={plantuml ?? ""} />
        </div>
      ) : (
        <Skeleton className="h-96 w-full" />
      )}
    </div>
  )
}

function DiagramImage({
  svgUrl,
  plantuml,
}: {
  svgUrl: string
  plantuml: string
}) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div className="space-y-3 py-8 text-center">
        <p className="text-sm text-muted-foreground">
          Unable to render diagram. The PlantUML server may be unavailable.
        </p>
        <p className="text-xs text-muted-foreground">
          Use &quot;View Source&quot; above to copy the PlantUML code and render
          it locally.
        </p>
        <a
          href="https://www.plantuml.com/plantuml/uml"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary underline"
        >
          Open PlantUML online editor
        </a>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={svgUrl}
      alt="Decision chart diagram"
      className="mx-auto max-w-full"
      onError={() => setFailed(true)}
    />
  )
}

function ChartSkeleton() {
  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-7 w-28" />
      </div>
      <Skeleton className="h-96 w-full rounded-xl" />
    </div>
  )
}
