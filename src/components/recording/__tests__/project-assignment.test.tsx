import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { http, HttpResponse } from "msw"
import { server } from "@/test/setup"

import { ProjectAssignment } from "../project-assignment"

const mockProjects = [
  { id: "proj-1", name: "Project Alpha", createdAt: "2026-03-12", updatedAt: "2026-03-12" },
  { id: "proj-2", name: "Project Beta", createdAt: "2026-03-12", updatedAt: "2026-03-12" },
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
}

beforeEach(() => {
  server.use(
    http.get("/api/projects", () => {
      return HttpResponse.json(mockProjects)
    })
  )
})

describe("ProjectAssignment", () => {
  it("shows dropdown for unassigned recordings", async () => {
    render(
      <ProjectAssignment

        currentProjectId={null}
        onAssign={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )

    const select = await screen.findByTestId("project-select")
    expect(select).toBeInTheDocument()
  })

  it("shows project name as static text for assigned recordings", async () => {
    render(
      <ProjectAssignment

        currentProjectId="proj-1"
        onAssign={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )

    expect(await screen.findByText("Project Alpha")).toBeInTheDocument()
    expect(screen.queryByTestId("project-select")).not.toBeInTheDocument()
  })

  it("selecting a project calls onAssign callback", async () => {
    const onAssign = vi.fn()
    const user = userEvent.setup()

    render(
      <ProjectAssignment

        currentProjectId={null}
        onAssign={onAssign}
      />,
      { wrapper: createWrapper() }
    )

    const select = await screen.findByTestId("project-select")
    // Wait for project options to load from MSW
    await screen.findByText("Project Alpha")
    await user.selectOptions(select, "proj-1")

    expect(onAssign).toHaveBeenCalledWith("proj-1")
  })

  it("Create new project option appears in dropdown", async () => {
    render(
      <ProjectAssignment

        currentProjectId={null}
        onAssign={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )

    const select = await screen.findByTestId("project-select")
    const options = select.querySelectorAll("option")
    const optionTexts = Array.from(options).map((o) => o.textContent)

    expect(optionTexts).toContain("+ Create new project")
  })
})
