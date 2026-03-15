"use client"

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react"

export interface AuthUser {
  id: string
  email: string
  name: string
  role: "admin" | "viewer"
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  isAdmin: boolean
  firstRun: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string, role?: string) => Promise<void>
  logout: () => Promise<void>
  refetch: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [firstRun, setFirstRun] = useState(false)

  const refetch = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/me")
      const data = await res.json()
      setUser(data.user ?? null)
      setFirstRun(data.firstRun ?? false)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    refetch().finally(() => setIsLoading(false))
  }, [refetch])

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || "Login failed")
    }
    const data = await res.json()
    setUser(data.user)
    setFirstRun(false)
  }, [])

  const register = useCallback(async (email: string, name: string, password: string, role?: string) => {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name, password, role }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || "Registration failed")
    }
    const data = await res.json()
    setUser(data.user)
    setFirstRun(false)
  }, [])

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" })
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAdmin: user?.role === "admin",
      firstRun,
      login,
      register,
      logout,
      refetch,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
