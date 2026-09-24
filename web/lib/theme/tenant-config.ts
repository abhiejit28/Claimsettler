export interface TenantConfig {
  id: string
  name: string
  logoUrl: string
  faviconUrl: string
  supportEmail: string
  colors: {
    // Full CSS color values (this project's generated globals.css sets
    // --primary etc. directly to oklch(...) values, not hsl(var(--x))
    // wrapped triples), so tenant overrides must be complete CSS colors —
    // any valid CSS color function/keyword works, not just oklch.
    primary: string
    primaryForeground: string
    accent?: string
  }
  footer?: {
    copyrightText?: string
    links?: { label: string; href: string }[]
  }
}

// Single-tenant, env-selected for Phase 1 — the backend has no tenant_id
// concept anywhere yet (see CLAUDE.md). Kept async and returning the same
// TenantConfig shape subdomain/path-based resolution would need, so that
// can be swapped in later (read a tenant id from middleware/headers instead
// of env vars) without touching any component that calls getTenantConfig().
export async function getTenantConfig(): Promise<TenantConfig> {
  return {
    id: process.env.NEXT_PUBLIC_TENANT_ID ?? "claimsettler-default",
    name: process.env.NEXT_PUBLIC_TENANT_NAME ?? "ClaimSettler",
    logoUrl: process.env.NEXT_PUBLIC_TENANT_LOGO_URL ?? "/logo.svg",
    faviconUrl: process.env.NEXT_PUBLIC_TENANT_FAVICON_URL ?? "/favicon.ico",
    supportEmail: process.env.NEXT_PUBLIC_TENANT_SUPPORT_EMAIL ?? "support@example.com",
    colors: {
      primary: process.env.NEXT_PUBLIC_TENANT_PRIMARY_COLOR ?? "oklch(0.205 0 0)",
      primaryForeground: process.env.NEXT_PUBLIC_TENANT_PRIMARY_FOREGROUND_COLOR ?? "oklch(0.985 0 0)",
      accent: process.env.NEXT_PUBLIC_TENANT_ACCENT_COLOR,
    },
  }
}
