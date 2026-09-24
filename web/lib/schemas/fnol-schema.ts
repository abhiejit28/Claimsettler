import { z } from "zod"

// Mirrors FNOLClaimRequest (src/claimsettler/api/schemas.py) field-for-field.
export const fnolSchema = z.object({
  claim_id: z.string().min(1, "Claim ID is required"),
  policy_id: z.string().min(1, "Policy ID is required"),
  product_id: z.string().min(1, "Product ID is required"),
  customer_name: z.string().min(2, "Enter the customer's full name"),
  claim_type: z.enum(["auto", "home", "commercial"], { message: "Select a claim type" }),
  claim_amount: z.number().positive("Enter an amount greater than zero"),
  incident_date: z.string().min(1, "Incident date is required"),
  reported_date: z.string().min(1, "Reported date is required"),
  narrative: z.string().min(10, "Add a bit more detail (10+ characters)").max(4000),
  // Phase 1 has no policy-management system — synthetic policy data is
  // entered as key/value pairs alongside the claim (see FNOLClaimRequest's
  // policy_data comment in schemas.py) and serialized to a flat object.
  policy_data: z.array(
    z.object({
      key: z.string().min(1, "Key is required"),
      value: z.string().min(1, "Value is required"),
    })
  ),
})

export type FnolFormValues = z.infer<typeof fnolSchema>
