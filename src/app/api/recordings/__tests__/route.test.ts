import { describe, it } from 'vitest';

describe('recordings API route', () => {
  it.todo('GET returns recordings list from local SQLite');
  it.todo('POST saves file locally and creates DB record');
  it.todo('POST with projectId proxies upload to FastAPI backend');
  it.todo('POST without projectId does not proxy to backend');
});
