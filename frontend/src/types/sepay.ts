export interface SePayCreateRequest {
  plan_id: string
  billing_cycle: "monthly" | "yearly"
  auto_renew?: boolean
}

export interface SePayCreditPurchaseRequest {
  credit_amount: number
}

export interface SePayQRResponse {
  order_id: string
  transaction_code: string
  qr_url: string
  amount: number
  description: string
  expires_at: string
}

export interface SePayStatusResponse {
  order_id: string
  transaction_code: string
  status: "pending" | "paid" | "expired"
  paid_at: string | null
}
