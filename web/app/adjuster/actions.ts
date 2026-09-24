"use server"

import { redirect } from "next/navigation"
import { setAdjusterToken, clearAdjusterToken } from "@/lib/cookies"

export async function submitAdjusterToken(_prevState: string | null, formData: FormData) {
  const token = String(formData.get("token") ?? "").trim()
  if (!token) return "Paste the bearer token printed to the API's server log."

  await setAdjusterToken(token)
  redirect("/adjuster")
}

export async function signOutAdjuster() {
  await clearAdjusterToken()
  redirect("/adjuster")
}
