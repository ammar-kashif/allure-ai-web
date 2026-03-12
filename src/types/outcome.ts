export type OutcomeType = 'decision' | 'action_item' | 'requirement' | 'blocker'

export type ExtractionStatus = 'none' | 'pending' | 'processing' | 'completed' | 'failed'

export interface EvidenceRef {
  segmentIndex: number
  speaker: string
  timestamp: number
  textSnippet?: string
}

export interface Outcome {
  id: string
  type: OutcomeType
  title: string
  detail: string
  confidence: number
  evidenceRefs: EvidenceRef[]
  promoted: boolean
  promotedId: string | null
}

export interface OutcomesResponse {
  jobId: string
  extractionStatus: ExtractionStatus
  outcomes: Outcome[]
}

export interface Task {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string
  sourceRecordingId: string
  backlink: string
  status: string
  createdAt: string
}

export interface RequirementRecord {
  id: string
  title: string
  detail: string
  sourceOutcomeId: string
  sourceRecordingId: string
  backlink: string
  createdAt: string
}
