import Link from "next/link"
import { Button } from "@/components/ui/button"
import { getTenantConfig } from "@/lib/theme/tenant-config"

export default async function Home() {
  const tenant = await getTenantConfig()

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-6 px-6 py-16 text-center">
      <h1 className="text-3xl font-semibold">{tenant.name}</h1>
      <p className="text-muted-foreground">Claims intake and adjuster review, Phase 1.</p>
      <div className="flex gap-4">
        <Button asChild>
          <Link href="/claims/new">File a claim</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/adjuster">Adjuster sign-in</Link>
        </Button>
      </div>
    </main>
  )
}
