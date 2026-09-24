// Mirrors src/claimsettler/shared/types.py::ClaimStatus and
// src/claimsettler/api/schemas.py exactly — keep in sync with the backend.

export type ClaimStatus = "claim_reported" | "under_review" | "approved" | "rejected"

export interface FNOLClaimRequest {
  claim_id: string
  policy_id: string
  product_id: string
  customer_name: string
  claim_type: string
  claim_amount: number
  incident_date: string
  reported_date: string
  narrative: string
  policy_data: Record<string, string>
}

export interface FNOLClaimResponse {
  claim_id: string
  status: ClaimStatus
  masking_report: Record<string, string>
  kma_document_id: string | null
}

export interface ClaimReviewResponse {
  claim_id: string
  policy_summary: string
  similar_claims_summary: string
  fraud_verdict: string
  fraud_confidence: number
  fraud_rule_hits: string[]
  fraud_explanation: string | null
  prediction_recommendation: string | null
  prediction_confidence: number | null
  prediction_rationale: string | null
}

export interface DecisionRequest {
  decision: "approve" | "reject"
  reasoning: string
  fraud_verdict: string
  prediction_recommendation?: string
  prediction_confidence?: number
}

export interface DecisionResponse {
  claim_id: string
  status: ClaimStatus
  trace_id: string
}
