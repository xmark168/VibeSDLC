export interface Plan {
  id: string
  code: string
  name: string
  description: string | null
  monthly_price: number | null
  yearly_price: number | null
  yearly_discount_percentage: number | null
  currency: string
  monthly_credits: number | null
  additional_credit_price: number | null // Price to buy 100 additional credits
  available_project: number | null
  is_active: boolean
  tier: string // 'free' | 'pay'
  sort_index: number
  is_featured: boolean
  is_custom_price: boolean
  features_text: string | null
  created_at: string
  updated_at: string
}

export interface PlanCreate {
  code: string
  name: string
  description?: string | null
  monthly_price?: number | null
  yearly_discount_percentage?: number | null
  currency?: string
  monthly_credits?: number | null
  additional_credit_price?: number | null
  available_project?: number | null
  is_active?: boolean
  tier?: string
  sort_index?: number
  is_featured?: boolean
  is_custom_price?: boolean
  features_text?: string | null
}

export interface PlanUpdate {
  code?: string
  name?: string
  description?: string | null
  monthly_price?: number | null
  yearly_discount_percentage?: number | null
  currency?: string
  monthly_credits?: number | null
  additional_credit_price?: number | null
  available_project?: number | null
  is_active?: boolean
  tier?: string
  sort_index?: number
  is_featured?: boolean
  is_custom_price?: boolean
  features_text?: string | null
}

export interface PlansResponse {
  data: Plan[]
  count: number
}

export interface PlanFilters {
  search?: string
  tier?: string
  is_active?: boolean
  is_featured?: boolean
  order_by?: 'sort_index' | 'price' | 'created_at' | 'name'
}
