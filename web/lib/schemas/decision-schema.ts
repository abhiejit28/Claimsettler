import { z } from "zod"

// Mirrors DecisionRequest (src/claimsettler/api/schemas.py); fraud_verdict,
// prediction_recommendation, and prediction_confidence are carried through
// from the review response, not re-entered by the adjuster.
export const decisionSchema = z.object({
  decision: z.enum(["approve", "reject"], { message: "Select approve or reject" }),
  reasoning: z.string().min(10, "Add a bit more detail (10+ characters)").max(2000),
})

export type DecisionFormValues = z.infer<typeof decisionSchema>
