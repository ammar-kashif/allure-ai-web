import { describe, it } from 'vitest';

describe('chunk-store', () => {
  it.todo('saveAudioChunk stores a chunk with recordingId and timestamp');
  it.todo('getAudioChunks returns chunks sorted by timestamp for a given recordingId');
  it.todo('clearAudioChunks removes all chunks for a given recordingId');
  it.todo('getIncompleteRecordingIds returns recordingIds with remaining chunks');
});
