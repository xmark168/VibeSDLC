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
  purchased_wallet: CreditWallet | null
}

export interface CreditActivity {
  id: string
  created_at: string
  activity_type: string
  amount: number
  tokens_used: number | null
  model_used: string | null
  llm_calls: number | null
  reason: string
  agent_name: string | null
  project_name: string | null
  story_title: string | null
  task_type: string | null
}

export interface CreditActivityResponse {
  total: number
  items: CreditActivity[]
  summary: {
    total_credits_spent: number
    total_tokens_used: number
    total_llm_calls: number
    top_agent: string | null
    top_model: string | null
  }
}
