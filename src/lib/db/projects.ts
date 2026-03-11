import { getDb } from "./index"
import type { Project } from "@/types/recording"

interface ProjectRow {
  id: string
  name: string
  created_at: string
  updated_at: string
}

function rowToProject(row: ProjectRow): Project {
  return {
    id: row.id,
    name: row.name,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export function getProjects(): Project[] {
  const db = getDb()
  const rows = db
    .prepare("SELECT * FROM projects ORDER BY created_at DESC")
    .all() as ProjectRow[]
  return rows.map(rowToProject)
}

export function createProject(name: string): Project {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO projects (id, name) VALUES (?, ?)`
  ).run(id, name)

  const row = db
    .prepare("SELECT * FROM projects WHERE id = ?")
    .get(id) as ProjectRow
  return rowToProject(row)
}
