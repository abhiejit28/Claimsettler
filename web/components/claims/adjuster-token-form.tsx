"use client"

import { useActionState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { submitAdjusterToken } from "@/app/adjuster/actions"

export function AdjusterTokenForm() {
  const [error, formAction, isPending] = useActionState(submitAdjusterToken, null)

  return (
    <form action={formAction} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="token">Adjuster bearer token</Label>
        <Input id="token" name="token" placeholder="cs_dev_..." autoComplete="off" />
        <p className="text-sm text-muted-foreground">
          Printed once to the API server&apos;s log on first boot:{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            [claimsettler] seeded dev adjuster user — bearer token: ...
          </code>
        </p>
        {error && <p className="text-sm font-medium text-destructive">{error}</p>}
      </div>
      <Button type="submit" disabled={isPending}>
        {isPending ? "Signing in..." : "Sign in"}
      </Button>
    </form>
  )
}
