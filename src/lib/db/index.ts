import Database from "better-sqlite3"
import { existsSync, mkdirSync, readFileSync } from "fs"
import { join, resolve } from "path"

const DB_DIR = join(process.cwd(), "public", "recordings")
const DB_PATH = join(DB_DIR, "allure-frontend.db")

function createDatabase(): Database.Database {
  if (!existsSync(DB_DIR)) {
    mkdirSync(DB_DIR, { recursive: true })
  }

  const db = new Database(DB_PATH)

  // Enable WAL mode and foreign keys
  db.pragma("journal_mode = WAL")
  db.pragma("foreign_keys = ON")

  // Run schema -- resolve from project root since __dirname is unreliable with bundlers
  const schemaPath = resolve(process.cwd(), "src/lib/db/schema.sql")
  if (existsSync(schemaPath)) {
    const schema = readFileSync(schemaPath, "utf-8")
    db.exec(schema)
  }

  // Migrate existing tables — ALTER TABLE for columns added after initial creation
  // (CREATE TABLE IF NOT EXISTS won't modify existing tables)
  const migrations: { table: string; column: string; definition: string }[] = [
    { table: "tasks", column: "priority", definition: "TEXT NOT NULL DEFAULT 'medium'" },
    { table: "tasks", column: "due_date", definition: "TEXT" },
    { table: "tasks", column: "assignee", definition: "TEXT" },
    { table: "tasks", column: "tags", definition: "TEXT NOT NULL DEFAULT '[]'" },
    { table: "recordings", column: "transcript_data", definition: "TEXT" },
  ]

  for (const m of migrations) {
    const columns = db.prepare(`PRAGMA table_info(${m.table})`).all() as { name: string }[]
    if (columns.length > 0 && !columns.some((c) => c.name === m.column)) {
      db.exec(`ALTER TABLE ${m.table} ADD COLUMN ${m.column} ${m.definition}`)
    }
  }

  return db
}

// Singleton — store on globalThis to survive Next.js dev HMR
const globalForDb = globalThis as unknown as { __allureDb: Database.Database | null }

export function getDb(): Database.Database {
  if (!globalForDb.__allureDb) {
    globalForDb.__allureDb = createDatabase()
  }
  return globalForDb.__allureDb
}

export default getDb

