import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { ClaimReviewResponse } from "@/lib/types/claims"

const FRAUD_VARIANT: Record<string, "default" | "destructive" | "secondary"> = {
  clean: "default",
  suspicious: "destructive",
  flagged: "destructive",
}

export function ClaimReviewPanel({ review }: { review: ClaimReviewResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Review — {review.claim_id}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <section>
          <h3 className="text-sm font-medium">Policy summary</h3>
          <p className="text-sm text-muted-foreground">{review.policy_summary}</p>
        </section>
        <section>
          <h3 className="text-sm font-medium">Similar claims</h3>
          <p className="text-sm text-muted-foreground">{review.similar_claims_summary}</p>
        </section>
        <Separator />
        <section className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium">Fraud verdict</h3>
            <Badge variant={FRAUD_VARIANT[review.fraud_verdict] ?? "secondary"}>
              {review.fraud_verdict}
            </Badge>
            <span className="text-sm text-muted-foreground">
              confidence {(review.fraud_confidence * 100).toFixed(0)}%
            </span>
          </div>
          {review.fraud_rule_hits.length > 0 && (
            <ul className="list-inside list-disc text-sm text-muted-foreground">
              {review.fraud_rule_hits.map((hit) => (
                <li key={hit}>{hit}</li>
              ))}
            </ul>
          )}
          {review.fraud_explanation && (
            <p className="text-sm text-muted-foreground">{review.fraud_explanation}</p>
          )}
        </section>
        {review.prediction_recommendation && (
          <>
            <Separator />
            <section className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">Prediction</h3>
                <Badge variant="secondary">{review.prediction_recommendation}</Badge>
                {review.prediction_confidence !== null && (
                  <span className="text-sm text-muted-foreground">
                    confidence {(review.prediction_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {review.prediction_rationale && (
                <p className="text-sm text-muted-foreground">{review.prediction_rationale}</p>
              )}
            </section>
          </>
        )}
      </CardContent>
    </Card>
  )
}
