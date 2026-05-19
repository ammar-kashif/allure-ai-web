export type RecordingStatus = 'unassigned' | 'processing' | 'ready' | 'error';

export interface Recording {
  id: string;
  title: string;
  description?: string | null;
  titleIsAuto?: boolean;
  durationMs: number;
  filePath: string | null;
  status: RecordingStatus;
  projectId: string | null;
  backendId: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface Utterance {
  id: string;
  speaker: string;
  text: string;
  startTime: number; // seconds
  endTime: number; // seconds
}

export interface SpeakerStat {
  label: string
  talkTimePct: number
  utteranceCount: number
  talkTime: number        // seconds
  wordCount: number
  wpm: number
  turns: number
  avgTurnDuration: number  // seconds
  pauses: number
  avgPauseDuration: number // seconds
  customLabel?: string     // user-assigned display name (empty = use label)
  role?: string            // e.g. "Presenter", "Participant", or custom
}

export interface Transcript {
  id: string;
  recordingId: string;
  utterances: Utterance[];
  speakers?: SpeakerStat[]       // from backend, optional for backward compat
  duration?: number              // total meeting duration in seconds
  processingTime?: number        // pipeline processing time in seconds
}
