import { redirect } from "next/navigation"
import { getAdjusterToken } from "@/lib/cookies"
import { getClaimReview } from "@/lib/api/claims.server"
import { ApiClientError } from "@/lib/api-client"
import { ClaimReviewPanel } from "@/components/claims/claim-review-panel"
import { DecisionForm } from "@/components/claims/decision-form"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { ClaimReviewResponse } from "@/lib/types/claims"

type LoadResult =
  | { ok: true; review: ClaimReviewResponse }
  | { ok: false; error: string }

async function loadReview(claimId: string): Promise<LoadResult> {
  try {
    return { ok: true, review: await getClaimReview(claimId) }
  } catch (e) {
    if (e instanceof ApiClientError && e.status === 401) redirect("/adjuster")
    return { ok: false, error: e instanceof ApiClientError ? e.message : "Unexpected error" }
  }
}

export default async function ClaimReviewPage({
  params,
}: PageProps<"/adjuster/claims/[claimId]">) {
  const { claimId } = await params
  const token = await getAdjusterToken()
  if (!token) redirect("/adjuster")

  const result = await loadReview(claimId)

  if (!result.ok) {
    return (
      <main className="mx-auto w-full max-w-3xl px-6 py-10">
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t load claim {claimId}</AlertTitle>
          <AlertDescription>{result.error}</AlertDescription>
        </Alert>
      </main>
    )
  }

  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-6 py-10">
      <ClaimReviewPanel review={result.review} />
      <DecisionForm review={result.review} />
    </main>
  )
}
