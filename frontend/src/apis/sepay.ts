import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  SePayCreateRequest,
  SePayCreditPurchaseRequest,
  SePayQRResponse,
  SePayStatusResponse,
} from "@/types/sepay"

export const sepayApi = {
  createPayment: async (data: SePayCreateRequest): Promise<SePayQRResponse> => {
    return __request<SePayQRResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/sepay/create",
      body: data,
    })
  },

  createCreditPurchase: async (
    data: SePayCreditPurchaseRequest,
  ): Promise<SePayQRResponse> => {
    return __request<SePayQRResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/sepay/credits/purchase",
      body: data,
    })
  },

  checkStatus: async (orderId: string): Promise<SePayStatusResponse> => {
    return __request<SePayStatusResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/sepay/status/${orderId}`,
    })
  },

  cancelPayment: async (orderId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: `/api/v1/sepay/cancel/${orderId}`,
    })
  },
}
