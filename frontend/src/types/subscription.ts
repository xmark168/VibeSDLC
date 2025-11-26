import type { Plan } from "./plan"

export interface Subscription {
  id: string
  status: 'active' | 'expired' | 'canceled' | 'pending'
  plan: Plan
  start_at: string
  end_at: string
  auto_renew: boolean
}

export interface CreditWallet {
  id: string
  total_credits: number
  used_credits: number
  remaining_credits: number
  period_start: string
  period_end: string
}

export interface UserSubscriptionResponse {
  subscription: Subscription | null
  credit_wallet: CreditWallet | null
}
