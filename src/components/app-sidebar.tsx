"use client"

import { useRouter } from "next/navigation"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { Home, Mic, CheckSquare, Milestone, Settings, LogOut, User } from "lucide-react"
import Link from "next/link"
import { useAuth } from "@/contexts/auth-context"
import { NotificationBell } from "@/components/notification/notification-bell"

const navItems = [
  { title: "Dashboard", url: "/", icon: Home },
  { title: "Recordings", url: "/recordings", icon: Mic },
  { title: "Tasks", url: "/tasks", icon: CheckSquare },
  { title: "Milestones", url: "/milestones", icon: Milestone },
]

export function AppSidebar() {
  const { user, logout, isAdmin } = useAuth()
  const router = useRouter()

  async function handleLogout() {
    await logout()
    router.push("/login")
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center justify-between px-2">
          <span className="font-heading text-lg font-bold tracking-tight">
            Allure
          </span>
          <NotificationBell />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    tooltip={item.title}
                    render={<Link href={item.url} />}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {user && (
            <>
              <SidebarSeparator />
              <SidebarMenuItem>
                <SidebarMenuButton tooltip={`${user.name} (${user.role})`} className="cursor-default">
                  <User />
                  <div className="flex flex-col items-start min-w-0">
                    <span className="truncate text-xs font-medium">{user.name}</span>
                    <span className="text-[10px] text-muted-foreground capitalize">{user.role}</span>
                  </div>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton tooltip="Sign out" onClick={handleLogout}>
                  <LogOut />
                  <span>Sign out</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </>
          )}
          {!user && (
            <SidebarMenuItem>
              <SidebarMenuButton
                tooltip="Settings"
                render={<Link href="#" />}
              >
                <Settings />
                <span>Settings</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
