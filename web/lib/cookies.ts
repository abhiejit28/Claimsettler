import "server-only"
import { cookies } from "next/headers"

// Single source of truth for every cookie this app sets.
export const COOKIE_NAMES = {
  // Phase 1 tradeoff: there is no backend login endpoint, so there is no
  // backend-issued session cookie either. The operator pastes the raw
  // dev-adjuster bearer token (printed once to the API's server log on
  // first boot) into a form; this cookie is what THIS Next.js app sets
  // after that paste, httpOnly on the Next.js side only. It is not a real
  // session — it is the raw bearer token, forwarded verbatim as
  // `Authorization: Bearer <token>` by the Route Handler proxy
  // (app/api/backend/[...path]/route.ts). A real deployment replaces the
  // paste-a-token screen with an actual login endpoint issuing its own
  // Set-Cookie session; see docs/architecturePlan.md "As Built" deviations
  // for why Phase 1 has no user-provisioning flow.
  adjusterToken: "cs_adjuster_token",
} as const

export async function getAdjusterToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_NAMES.adjusterToken)?.value
}

export async function setAdjusterToken(token: string): Promise<void> {
  const store = await cookies()
  store.set(COOKIE_NAMES.adjusterToken, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12, // 12h — matches the dev-adjuster token's practical lifetime (regenerated per fresh DB)
  })
}

export async function clearAdjusterToken(): Promise<void> {
  const store = await cookies()
  store.delete(COOKIE_NAMES.adjusterToken)
}
