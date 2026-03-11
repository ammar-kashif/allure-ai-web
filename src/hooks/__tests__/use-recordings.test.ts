import { describe, it } from 'vitest';

describe('useRecordings', () => {
  it.todo('fetches recording list from /api/recordings');
  it.todo('unassigned - recordings with no projectId are not sent to backend');

  describe('useRecordingStatus', () => {
    it.todo('polling - polls /api/recordings/[id]/status every 3s when processing');
    it.todo('polling - stops polling when status is ready');
    it.todo('polling - stops polling when status is error');
  });

  describe('useUploadRecording', () => {
    it.todo('POSTs FormData to /api/recordings');
  });
});
