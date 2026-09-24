"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function ClaimLookupForm() {
  const router = useRouter()
  const [claimId, setClaimId] = useState("")

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (claimId.trim()) router.push(`/adjuster/claims/${encodeURIComponent(claimId.trim())}`)
      }}
      className="space-y-4"
    >
      <div className="space-y-2">
        <Label htmlFor="claimId">Claim ID</Label>
        <Input id="claimId" value={claimId} onChange={(e) => setClaimId(e.target.value)} />
      </div>
      <Button type="submit">Review claim</Button>
    </form>
  )
}
