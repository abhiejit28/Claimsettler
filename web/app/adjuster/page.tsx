import { getAdjusterToken } from "@/lib/cookies"
import { AdjusterTokenForm } from "@/components/claims/adjuster-token-form"
import { ClaimLookupForm } from "@/components/claims/claim-lookup-form"
import { signOutAdjuster } from "@/app/adjuster/actions"
import { Button } from "@/components/ui/button"

export default async function AdjusterPage() {
  const token = await getAdjusterToken()

  if (!token) {
    return (
      <main className="mx-auto w-full max-w-sm px-6 py-10">
        <h1 className="mb-1 text-2xl font-semibold">Adjuster sign-in</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Phase 1 has no login endpoint — paste the dev-adjuster bearer token from the API
          server&apos;s log.
        </p>
        <AdjusterTokenForm />
      </main>
    )
  }

  return (
    <main className="mx-auto w-full max-w-sm px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Review a claim</h1>
        <form action={signOutAdjuster}>
          <Button type="submit" variant="outline" size="sm">
            Sign out
          </Button>
        </form>
      </div>
      <ClaimLookupForm />
    </main>
  )
}
