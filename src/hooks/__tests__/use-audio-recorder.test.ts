import { describe, it } from 'vitest';

describe('useAudioRecorder', () => {
  it.todo('captures audio with audio/webm;codecs=opus MIME type');
  it.todo('saves chunks to IndexedDB via saveAudioChunk on ondataavailable');
  it.todo('assembles final blob from IndexedDB chunks on stop');
  it.todo('updates Zustand store isRecording state');
  it.todo('shows elapsed time based on startedAt');
  it.todo('handles getUserMedia rejection with toast error');
});
