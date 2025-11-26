import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import type { Plan, PlanCreate } from "@/types/plan"
import { useCreatePlan, useUpdatePlan } from "@/queries/plans"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Loader2 } from "lucide-react"

const planFormSchema = z.object({
  code: z.string().min(1, "Code is required").max(50),
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().optional(),
  monthly_price: z.coerce.number().min(0, "Monthly price must be positive").optional().nullable(),
  yearly_discount_percentage: z.coerce.number().min(0).max(100, "Discount must be between 0-100%").optional().nullable(),
  currency: z.string().default("VND"),
  monthly_credits: z.coerce.number().int().min(0).optional().nullable(),
  additional_credit_price: z.coerce.number().int().min(0).optional().nullable(),
  available_project: z.coerce.number().int().min(0).optional().nullable(),
  is_active: z.boolean().default(true),
  tier: z.enum(["free", "pay"]).default("pay"),
  sort_index: z.coerce.number().int().min(0).default(0),
  is_featured: z.boolean().default(false),
  is_custom_price: z.boolean().default(false),
  features_text: z.string().optional(),
})

type PlanFormValues = z.infer<typeof planFormSchema>

interface PlanDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  plan?: Plan
  initialData?: Partial<Plan>
  onSuccess?: () => void
}

export function PlanDialog({ open, onOpenChange, plan, initialData, onSuccess }: PlanDialogProps) {
  const isEditing = !!plan
  const createPlan = useCreatePlan()
  const updatePlan = useUpdatePlan()

  const form = useForm({
    resolver: zodResolver(planFormSchema),
    defaultValues: {
      code: "",
      name: "",
      description: "",
      monthly_price: null,
      yearly_discount_percentage: null,
      currency: "VND",
      monthly_credits: null,
      additional_credit_price: null,
      available_project: null,
      is_active: true,
      tier: "pay" as "free" | "pay",
      sort_index: 0,
      is_featured: false,
      is_custom_price: false,
      features_text: "",
    },
  })

  // Update form when plan or initialData changes
  useEffect(() => {
    if (plan) {
      // Calculate discount from existing prices
      const discount = plan.yearly_discount_percentage ?? null

      form.reset({
        code: plan.code,
        name: plan.name,
        description: plan.description || "",
        monthly_price: plan.monthly_price,
        yearly_discount_percentage: discount,
        currency: plan.currency || "VND",
        monthly_credits: plan.monthly_credits,
        additional_credit_price: plan.additional_credit_price,
        available_project: plan.available_project,
        is_active: plan.is_active,
        tier: plan.tier as any,
        sort_index: plan.sort_index,
        is_featured: plan.is_featured,
        is_custom_price: plan.is_custom_price,
        features_text: plan.features_text || "",
      })
    } else if (initialData) {
      const discount = initialData.yearly_discount_percentage ?? null

      form.reset({
        code: initialData.code || "",
        name: initialData.name || "",
        description: initialData.description || "",
        monthly_price: initialData.monthly_price,
        yearly_discount_percentage: discount,
        currency: initialData.currency || "VND",
        monthly_credits: initialData.monthly_credits,
        additional_credit_price: initialData.additional_credit_price,
        available_project: initialData.available_project,
        is_active: initialData.is_active ?? true,
        tier: (initialData.tier || "pay") as any,
        sort_index: initialData.sort_index || 0,
        is_featured: initialData.is_featured || false,
        is_custom_price: initialData.is_custom_price || false,
        features_text: initialData.features_text || "",
      })
    } else {
      form.reset({
        code: "",
        name: "",
        description: "",
        monthly_price: null,
        yearly_discount_percentage: null,
        currency: "VND",
        monthly_credits: null,
        additional_credit_price: null,
        available_project: null,
        is_active: true,
        tier: "pay",
        sort_index: 0,
        is_featured: false,
        is_custom_price: false,
        features_text: "",
      })
    }
  }, [plan, initialData, form])

  const onSubmit = async (data: z.infer<typeof planFormSchema>) => {
    try {
      const payload: any = {
        code: data.code,
        name: data.name,
        description: data.description || null,
        monthly_price: data.monthly_price ?? null,
        yearly_discount_percentage: data.yearly_discount_percentage ?? null,
        currency: data.currency,
        monthly_credits: data.monthly_credits ?? null,
        additional_credit_price: data.additional_credit_price ?? null,
        available_project: data.available_project ?? null,
        is_active: data.is_active,
        tier: data.tier,
        sort_index: data.sort_index,
        is_featured: data.is_featured,
        is_custom_price: data.is_custom_price,
        features_text: data.features_text || null,
      }

      if (isEditing) {
        await updatePlan.mutateAsync({ planId: plan.id, data: payload })
      } else {
        await createPlan.mutateAsync(payload)
      }

      form.reset()
      onSuccess?.()
    } catch (error) {
      // Error handling is done in the mutation hooks
      console.error("Form submission error:", error)
    }
  }

  const isLoading = createPlan.isPending || updatePlan.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-slate-900 border-slate-800 text-white">
        <DialogHeader>
          <DialogTitle className="text-2xl font-serif">
            {isEditing ? "Edit Plan" : "Create New Plan"}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {isEditing
              ? "Update the plan details below."
              : "Fill in the details to create a new subscription plan."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-amber-400 border-b border-slate-800 pb-2">
                Basic Information
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Plan Code *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="e.g., PRO, FREE, ENTERPRISE"
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Unique identifier for the plan
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Plan Name *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="e.g., Professional Plan"
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Display name for the plan
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder="Describe what this plan offers..."
                        className="bg-slate-950/50 border-slate-700 text-white min-h-[80px]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Pricing */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-amber-400 border-b border-slate-800 pb-2">
                Pricing
              </h3>

              <div className="grid grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="monthly_price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Monthly Price</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          step="1"
                          placeholder="0"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Leave empty if not offered
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="yearly_discount_percentage"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Yearly Discount %</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          step="0.1"
                          placeholder="0"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Discount percentage (0-100%)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="currency"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Currency</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-950/50 border-slate-700 text-white">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="VND">VND</SelectItem>
                          <SelectItem value="USD">USD</SelectItem>
                          <SelectItem value="EUR">EUR</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Yearly price calculation display */}
              {form.watch("monthly_price") && form.watch("yearly_discount_percentage") && (
                <div className="text-sm text-emerald-400 flex items-center gap-2">
                  <span>Calculated yearly price: {
                    (() => {
                      const monthly = form.watch("monthly_price")
                      const discount = form.watch("yearly_discount_percentage")
                      if (monthly && discount != null) {
                        const annualPrice = monthly * 12
                        const yearlyPrice = Math.round(annualPrice * (1 - discount / 100))
                        return new Intl.NumberFormat('vi-VN', {
                          style: 'currency',
                          currency: 'VND',
                        }).format(yearlyPrice)
                      }
                      return "0"
                    })()
                  }</span>
                </div>
              )}
            </div>

            {/* Features & Limits */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-amber-400 border-b border-slate-800 pb-2">
                Features & Limits
              </h3>

              <div className="grid grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="monthly_credits"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Monthly Credits</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          placeholder="1000"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="additional_credit_price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Price per 100 Credits</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          placeholder="10000"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Price to buy 100 additional credits
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="available_project"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Available Projects</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          placeholder="10"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="features_text"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Features Text</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder="List plan features (one per line or comma separated)"
                        className="bg-slate-950/50 border-slate-700 text-white min-h-[80px]"
                      />
                    </FormControl>
                    <FormDescription className="text-slate-500 text-xs">
                      Additional features description
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Plan Configuration */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-amber-400 border-b border-slate-800 pb-2">
                Configuration
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="tier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tier</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-950/50 border-slate-700 text-white">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="free">Free</SelectItem>
                          <SelectItem value="pay">Pay</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="sort_index"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sort Index</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          placeholder="0"
                          value={field.value == null ? "" : String(field.value)}
                          onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : 0)}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="bg-slate-950/50 border-slate-700 text-white"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-500 text-xs">
                        Display order (lower = first)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-3 gap-6 pt-4">
                <FormField
                  control={form.control}
                  name="is_active"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border border-slate-800 p-4 bg-slate-950/30">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">Active</FormLabel>
                        <FormDescription className="text-xs text-slate-500">
                          Enable this plan
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="is_featured"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border border-slate-800 p-4 bg-slate-950/30">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">Featured</FormLabel>
                        <FormDescription className="text-xs text-slate-500">
                          Highlight plan
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="is_custom_price"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border border-slate-800 p-4 bg-slate-950/30">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">Custom Price</FormLabel>
                        <FormDescription className="text-xs text-slate-500">
                          Show "Custom"
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                className="bg-slate-800 border-slate-700 text-white hover:bg-slate-700"
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="bg-amber-600 hover:bg-amber-700 text-white"
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isEditing ? "Update Plan" : "Create Plan"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
