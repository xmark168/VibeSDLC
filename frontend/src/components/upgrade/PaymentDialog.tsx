import { CheckCircle, Copy, ExternalLink, Loader2, XCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "@/lib/toast"
import { usePaymentStatus } from "@/queries/payments"
import type { PaymentLinkResponse } from "@/types/payment"

interface PaymentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  paymentData: PaymentLinkResponse | null
  onSuccess: () => void
  onCancel: () => void
}

export function PaymentDialog({
  open,
  onOpenChange,
  paymentData,
  onSuccess,
  onCancel,
}: PaymentDialogProps) {
  const [copiedQR, setCopiedQR] = useState(false)

  // Poll payment status
  const { data: statusData, isLoading: statusLoading } = usePaymentStatus(
    paymentData?.order_id || null,
    { enabled: open && !!paymentData },
  )

  // Handle payment completion
  useEffect(() => {
    if (statusData?.status === "paid") {
      toast.success("Payment successful! Your subscription is now active.")
      onSuccess()
    } else if (
      statusData?.status === "failed" ||
      statusData?.status === "canceled"
    ) {
      toast.error("Payment failed or was canceled.")
      onCancel()
    }
  }, [statusData, onSuccess, onCancel])

  const handleCopyQRCode = () => {
    if (paymentData?.checkout_url) {
      navigator.clipboard.writeText(paymentData.checkout_url)
      setCopiedQR(true)
      toast.success("Payment link copied!")
      setTimeout(() => setCopiedQR(false), 2000)
    }
  }

  const handleOpenCheckoutUrl = () => {
    if (paymentData?.checkout_url) {
      window.open(paymentData.checkout_url, "_blank")
    }
  }

  if (!paymentData) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Complete Your Payment</DialogTitle>
          <DialogDescription>
            Scan the QR code below using your banking app to complete the
            payment
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* QR Code Display */}
          <div className="flex flex-col items-center justify-center p-6 bg-white rounded-lg border">
            {paymentData.qr_code ? (
              <img
                src={paymentData.qr_code}
                alt="Payment QR Code"
                className="w-64 h-64 object-contain"
              />
            ) : (
              <div className="w-64 h-64 flex items-center justify-center bg-muted rounded">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>

          {/* Payment Details */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Amount:</span>
              <span className="font-semibold">
                {new Intl.NumberFormat("vi-VN", {
                  style: "currency",
                  currency: "VND",
                }).format(paymentData.amount)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Description:</span>
              <span className="font-medium">{paymentData.description}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Order Code:</span>
              <span className="font-mono text-xs">
                {paymentData.payos_order_code}
              </span>
            </div>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center justify-center gap-2 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
            {statusLoading || statusData?.status === "pending" ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
                <span className="text-sm text-blue-600 dark:text-blue-400">
                  Waiting for payment...
                </span>
              </>
            ) : statusData?.status === "paid" ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                <span className="text-sm text-green-600 dark:text-green-400">
                  Payment successful!
                </span>
              </>
            ) : statusData?.status === "failed" ||
              statusData?.status === "canceled" ? (
              <>
                <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                <span className="text-sm text-red-600 dark:text-red-400">
                  Payment failed
                </span>
              </>
            ) : null}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleCopyQRCode}
              className="flex-1"
            >
              <Copy className="w-4 h-4 mr-2" />
              {copiedQR ? "Copied!" : "Copy Link"}
            </Button>
            <Button onClick={handleOpenCheckoutUrl} className="flex-1">
              <ExternalLink className="w-4 h-4 mr-2" />
              Open in Browser
            </Button>
          </div>

          {/* Help Text */}
          <p className="text-xs text-center text-muted-foreground">
            Having trouble? Contact support for assistance.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
