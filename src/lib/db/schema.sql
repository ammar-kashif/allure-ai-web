CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recordings (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  duration_ms INTEGER DEFAULT 0,
  file_path TEXT,
  status TEXT NOT NULL DEFAULT 'unassigned',
  project_id TEXT,
  backend_id TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS outcomes (
  id TEXT PRIMARY KEY,
  recording_id TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('decision', 'action_item', 'requirement', 'blocker')),
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  confidence REAL NOT NULL DEFAULT 0.0,
  evidence_refs TEXT NOT NULL DEFAULT '[]',
  promoted INTEGER NOT NULL DEFAULT 0,
  promoted_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (recording_id) REFERENCES recordings(id)
);

-- Note: If upgrading from a previous schema, delete the existing DB file (allure.db)
-- since CREATE TABLE IF NOT EXISTS will not alter an existing table.
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  source_outcome_id TEXT,
  source_recording_id TEXT,
  backlink TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  priority TEXT NOT NULL DEFAULT 'medium',
  due_date TEXT,
  assignee TEXT,
  tags TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_outcome_id) REFERENCES outcomes(id),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);

CREATE TABLE IF NOT EXISTS requirement_records (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  source_outcome_id TEXT,
  source_recording_id TEXT,
  backlink TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_outcome_id) REFERENCES outcomes(id),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('prd', 'user_flow', 'erd')),
  content TEXT NOT NULL,
  source_recording_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);

