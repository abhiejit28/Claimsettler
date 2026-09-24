"use client"

import { useState } from "react"
import { useFieldArray, useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { fnolSchema, type FnolFormValues } from "@/lib/schemas/fnol-schema"
import { claimsApi } from "@/lib/api/claims"
import { ApiClientError } from "@/lib/api-client"
import type { FNOLClaimResponse } from "@/lib/types/claims"

export function FnolForm() {
  const [result, setResult] = useState<FNOLClaimResponse | null>(null)

  const form = useForm<FnolFormValues>({
    resolver: zodResolver(fnolSchema),
    defaultValues: {
      claim_id: "",
      policy_id: "",
      product_id: "",
      customer_name: "",
      claim_type: "auto",
      claim_amount: 0,
      incident_date: "",
      reported_date: "",
      narrative: "",
      policy_data: [],
    },
  })

  const policyDataFields = useFieldArray({ control: form.control, name: "policy_data" })

  async function onSubmit(values: FnolFormValues) {
    try {
      const policy_data = Object.fromEntries(values.policy_data.map((f) => [f.key, f.value]))
      const response = await claimsApi.create({ ...values, policy_data })
      setResult(response)
      toast.success(`Claim ${response.claim_id} submitted`)
      form.reset()
      policyDataFields.replace([])
    } catch (e) {
      toast.error(e instanceof ApiClientError ? e.message : "Failed to submit claim")
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="claim_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Claim ID</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="policy_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Policy ID</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="product_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Product ID</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="customer_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Customer name</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="claim_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Claim type</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a claim type" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="auto">Auto</SelectItem>
                    <SelectItem value="home">Home</SelectItem>
                    <SelectItem value="commercial">Commercial</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="claim_amount"
            render={({ field: { onChange, ...field } }) => (
              <FormItem>
                <FormLabel>Claim amount</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="0.01"
                    {...field}
                    onChange={(e) => onChange(e.target.valueAsNumber)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="incident_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Incident date</FormLabel>
                <FormControl>
                  <Input type="date" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="reported_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Reported date</FormLabel>
                <FormControl>
                  <Input type="date" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="narrative"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Narrative</FormLabel>
              <FormControl>
                <Textarea rows={4} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Policy data</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {policyDataFields.fields.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No policy data entered yet. Phase 1 has no policy-management system, so synthetic
                policy details are supplied here.
              </p>
            )}
            {policyDataFields.fields.map((field, index) => (
              <div key={field.id} className="flex items-end gap-2">
                <FormField
                  control={form.control}
                  name={`policy_data.${index}.key`}
                  render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormLabel>Key</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name={`policy_data.${index}.value`}
                  render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormLabel>Value</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="button" variant="outline" onClick={() => policyDataFields.remove(index)}>
                  Remove
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => policyDataFields.append({ key: "", value: "" })}
            >
              Add policy field
            </Button>
          </CardContent>
        </Card>

        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Submitting..." : "Submit claim"}
        </Button>
      </form>

      {result && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Submission result</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Claim ID: <span className="font-mono">{result.claim_id}</span>
            </p>
            <p>Status: {result.status}</p>
            {result.kma_document_id && (
              <p>
                KMA document: <span className="font-mono">{result.kma_document_id}</span>
              </p>
            )}
            {Object.keys(result.masking_report).length > 0 && (
              <div>
                <p className="mt-2 font-medium">Masking report</p>
                <ul className="list-inside list-disc">
                  {Object.entries(result.masking_report).map(([field, note]) => (
                    <li key={field}>
                      {field}: {note}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </Form>
  )
}
