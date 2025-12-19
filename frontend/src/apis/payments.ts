import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  CreatePaymentRequest,
  InvoiceDetail,
  Order,
  PaymentHistory,
  PaymentLinkResponse,
  PaymentStatusResponse,
} from "@/types/payment"

export const paymentsApi = {
  // Create payment link
  createPaymentLink: async (
    body: CreatePaymentRequest,
  ): Promise<PaymentLinkResponse> => {
    return __request<PaymentLinkResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/payments/create",
      body,
    })
  },

  // Purchase credits
  purchaseCredits: async (
    credit_amount: number,
  ): Promise<PaymentLinkResponse> => {
    return __request<PaymentLinkResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/payments/credits/purchase",
      body: { credit_amount },
    })
  },

  // Check payment status
  getPaymentStatus: async (orderId: string): Promise<PaymentStatusResponse> => {
    return __request<PaymentStatusResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/payments/status/${orderId}`,
    })
  },

  // Get order by ID
  getOrderById: async (orderId: string): Promise<Order> => {
    return __request<Order>(OpenAPI, {
      method: "GET",
      url: `/api/v1/orders/${orderId}`,
    })
  },

  // Get payment history
  getPaymentHistory: async (params?: {
    limit?: number
    offset?: number
  }): Promise<PaymentHistory> => {
    return __request<PaymentHistory>(OpenAPI, {
      method: "GET",
      url: "/api/v1/payments/history",
      query: params,
    })
  },

  // Get invoice details
  getInvoice: async (orderId: string): Promise<InvoiceDetail> => {
    return __request<InvoiceDetail>(OpenAPI, {
      method: "GET",
      url: `/api/v1/payments/invoice/${orderId}`,
    })
  },

  // Manually sync payment status with PayOS using orderCode (for local dev)
  syncPaymentStatusByCode: async (
    orderCode: number,
  ): Promise<{ message: string; status: string; subscription_id?: string }> => {
    return __request<{
      message: string
      status: string
      subscription_id?: string
    }>(OpenAPI, {
      method: "POST",
      url: `/api/v1/payments/sync-status-by-code/${orderCode}`,
    })
  },
}
