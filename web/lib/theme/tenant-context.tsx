"use client"

import { createContext, useContext } from "react"
import type { TenantConfig } from "@/lib/theme/tenant-config"

const TenantContext = createContext<TenantConfig | null>(null)

export function TenantProvider({
  tenant,
  children,
}: {
  tenant: TenantConfig
  children: React.ReactNode
}) {
  return <TenantContext.Provider value={tenant}>{children}</TenantContext.Provider>
}

export function useTenant(): TenantConfig {
  const tenant = useContext(TenantContext)
  if (!tenant) {
    throw new Error("useTenant must be used within a TenantProvider")
  }
  return tenant
}
