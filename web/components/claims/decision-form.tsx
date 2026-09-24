"use client"

import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { decisionSchema, type DecisionFormValues } from "@/lib/schemas/decision-schema"
import { claimsApi } from "@/lib/api/claims"
import { ApiClientError } from "@/lib/api-client"
import type { ClaimReviewResponse } from "@/lib/types/claims"

export function DecisionForm({ review }: { review: ClaimReviewResponse }) {
  const router = useRouter()

  const form = useForm<DecisionFormValues>({
    resolver: zodResolver(decisionSchema),
    defaultValues: { decision: "approve", reasoning: "" },
  })

  async function onSubmit(values: DecisionFormValues) {
    try {
      const response = await claimsApi.decide(review.claim_id, {
        decision: values.decision,
        reasoning: values.reasoning,
        fraud_verdict: review.fraud_verdict,
        prediction_recommendation: review.prediction_recommendation ?? undefined,
        prediction_confidence: review.prediction_confidence ?? undefined,
      })
      toast.success(`Decision recorded — status ${response.status} (trace ${response.trace_id})`)
      router.refresh()
    } catch (e) {
      toast.error(e instanceof ApiClientError ? e.message : "Failed to record decision")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Decision</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="decision"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Decision</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="approve">Approve</SelectItem>
                      <SelectItem value="reject">Reject</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="reasoning"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Reasoning</FormLabel>
                  <FormControl>
                    <Textarea rows={4} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? "Submitting..." : "Submit decision"}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
