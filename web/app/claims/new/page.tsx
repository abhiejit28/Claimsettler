import { FnolForm } from "@/components/claims/fnol-form"

export default function NewClaimPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold">File a new claim</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Submit a First Notice of Loss (FNOL) to start the claims process.
      </p>
      <FnolForm />
    </main>
  )
}
