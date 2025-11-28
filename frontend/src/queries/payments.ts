import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { paymentsApi } from "@/apis/payments"
import type { CreatePaymentRequest } from "@/types/payment"
import toast from "react-hot-toast"

// Query Keys
export const paymentQueryKeys = {
  all: ["payments"] as const,
  status: (orderId: string) => [...paymentQueryKeys.all, "status", orderId] as const,
  order: (orderId: string) => [...paymentQueryKeys.all, "order", orderId] as const,
  history: (params?: any) => [...paymentQueryKeys.all, "history", params] as const,
  invoice: (orderId: string) => [...paymentQueryKeys.all, "invoice", orderId] as const,
}

// Create Payment Link Mutation
export function useCreatePaymentLink() {
  return useMutation({
    mutationFn: (data: CreatePaymentRequest) => paymentsApi.createPaymentLink(data),
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to create payment"
      toast.error(message)
    },
  })
}

// Poll Payment Status
export function usePaymentStatus(orderId: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: paymentQueryKeys.status(orderId || ""),
    queryFn: () => paymentsApi.getPaymentStatus(orderId!),
    enabled: (options?.enabled ?? true) && !!orderId,
    refetchInterval: 3000, // Poll every 3 seconds
    refetchIntervalInBackground: false,
    retry: false,
  })
}

// Get Order Details
export function useOrder(orderId: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: paymentQueryKeys.order(orderId || ""),
    queryFn: () => paymentsApi.getOrderById(orderId!),
    enabled: (options?.enabled ?? true) && !!orderId,
  })
}

// Get Payment History
export function usePaymentHistory(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: paymentQueryKeys.history(params),
    queryFn: () => paymentsApi.getPaymentHistory(params),
  })
}

// Get Invoice Details
export function useInvoice(orderId: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: paymentQueryKeys.invoice(orderId || ""),
    queryFn: () => paymentsApi.getInvoice(orderId!),
    enabled: (options?.enabled ?? true) && !!orderId,
  })
}
