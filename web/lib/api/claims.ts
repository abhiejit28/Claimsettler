// Client-safe wrappers — call through the same-origin proxy
// (app/api/backend/[...path]/route.ts). Used from Client Components.
import { api } from "@/lib/api-client"
import type { DecisionRequest, DecisionResponse, FNOLClaimRequest, FNOLClaimResponse } from "@/lib/types/claims"

export const claimsApi = {
  create: (data: FNOLClaimRequest) => api.post<FNOLClaimResponse>("/claims", data),
  decide: (claimId: string, data: DecisionRequest) =>
    api.post<DecisionResponse>(`/claims/${claimId}/decision`, data),
}
