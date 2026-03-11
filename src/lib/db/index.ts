import Database from "better-sqlite3"
import { existsSync, mkdirSync, readFileSync } from "fs"
import { join, resolve } from "path"
import { homedir } from "os"

const DB_DIR = join(homedir(), ".allure")
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

  return db
}

// Singleton
let _db: Database.Database | null = null

export function getDb(): Database.Database {
  if (!_db) {
    _db = createDatabase()
  }
  return _db
}

export default getDb
