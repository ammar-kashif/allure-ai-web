export type RecordingStatus = 'unassigned' | 'processing' | 'ready' | 'error';

export interface Recording {
  id: string;
  title: string;
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

export interface SpeakerStats {
  label: string;
  talkTimePct: number;
  utteranceCount: number;
  role?: string;
}

export interface Transcript {
  id: string;
  recordingId: string;
  duration: number; // seconds
  speakers: SpeakerStats[];
  utterances: Utterance[];
}
