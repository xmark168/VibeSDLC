export interface PaymentItem {
  name: string
  quantity: number
  price: number
}

export interface CreatePaymentRequest {
  plan_id: string
  billing_cycle: 'monthly' | 'yearly'
  return_url?: string
  cancel_url?: string
}

export interface PaymentLinkResponse {
  order_id: string
  payos_order_code: number
  checkout_url: string
  qr_code: string  // Base64 QR code image
  amount: number
  description: string
}

export interface PaymentStatusResponse {
  order_id: string
  status: 'pending' | 'paid' | 'failed' | 'canceled'
  paid_at: string | null
  payos_transaction_id: string | null
}

export interface Order {
  id: string
  user_id?: string
  order_type: 'subscription' | 'addon'
  subscription_id?: string | null
  amount: number
  status: 'PENDING' | 'PAID' | 'FAILED' | 'CANCELED'
  paid_at: string | null
  is_active?: boolean
  payos_order_code: number | null
  payos_transaction_id?: string | null
  payment_link_id?: string | null
  qr_code?: string | null
  checkout_url?: string | null
  billing_cycle: string | null
  plan_code: string | null
  created_at: string
  updated_at?: string
}

export interface PaymentHistory {
  data: Order[]
  total: number
  limit: number
  offset: number
}

export interface Invoice {
  id: string
  invoice_number: string
  billing_name: string
  billing_address: string
  amount: number
  currency: string
  issue_date: string
  status: 'DRAFT' | 'PAID' | 'CANCELLED'
}

export interface PlanInfo {
  name: string
  code: string
  description: string | null
  monthly_credits: number | null
  available_project: number | null
}

export interface InvoiceDetail {
  invoice: Invoice
  order: Order
  plan: PlanInfo | null
}
