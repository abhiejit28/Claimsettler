import "server-only"
import { getAdjusterToken } from "@/lib/cookies"
import { ApiClientError } from "@/lib/api-client"
import type { ClaimReviewResponse } from "@/lib/types/claims"

// Server Components already have direct access to the request cookie and
// run trusted server code, so this calls the FastAPI backend directly
// rather than round-tripping through our own proxy — see api-client.md's
// guidance to skip the client wrapper's browser assumptions here.
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000"

export async function getClaimReview(claimId: string): Promise<ClaimReviewResponse> {
  const token = await getAdjusterToken()
  const res = await fetch(`${API_BASE_URL}/claims/${claimId}/review`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  })

  if (!res.ok) {
    let details: unknown
    try {
      details = await res.json()
    } catch {
      /* body wasn't JSON */
    }
    const body = details as { detail?: string } | undefined
    throw new ApiClientError(res.status, body?.detail ?? res.statusText, details)
  }

  return res.json() as Promise<ClaimReviewResponse>
}
