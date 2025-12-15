import { useState, useEffect, useCallback } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2, CheckCircle, XCircle, Clock, Copy, RefreshCw } from "lucide-react"
import { sepayApi } from "@/apis/sepay"
import type { SePayQRResponse, SePayStatusResponse } from "@/types/sepay"
import { toast } from "@/lib/toast"
import { formatPrice } from "@/apis/plans"

interface SePayQRDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  qrData: SePayQRResponse | null
  onSuccess: () => void
  onCancel: () => void
}

export function SePayQRDialog({
  open,
  onOpenChange,
  qrData,
  onSuccess,
  onCancel,
}: SePayQRDialogProps) {
  const [status, setStatus] = useState<SePayStatusResponse | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [timeLeft, setTimeLeft] = useState<number>(0)
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null)

  // Fetch QR image with authentication
  useEffect(() => {
    if (!qrData) return

    const fetchQRImage = async () => {
      try {
        const token = localStorage.getItem("access_token")
        const response = await fetch(`${import.meta.env.VITE_API_URL}${qrData.qr_url}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const blob = await response.blob()
          const objectUrl = URL.createObjectURL(blob)
          setQrImageUrl(objectUrl)
        }
      } catch (error) {
        console.error("Failed to fetch QR image:", error)
      }
    }

    fetchQRImage()

    // Cleanup object URL
    return () => {
      if (qrImageUrl) {
        URL.revokeObjectURL(qrImageUrl)
      }
    }
  }, [qrData?.qr_url])

  // Reset state when qrData changes (new payment) or dialog closes
  useEffect(() => {
    if (qrData) {
      // New QR data - reset status to start fresh
      setStatus(null)
      setIsPolling(false)
    }
  }, [qrData?.order_id])

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setStatus(null)
      setIsPolling(false)
      setTimeLeft(0)
    }
  }, [open])

  const checkPaymentStatus = useCallback(async () => {
    if (!qrData) return
    
    try {
      const result = await sepayApi.checkStatus(qrData.order_id)
      setStatus(result)
      
      if (result.status === "paid") {
        setIsPolling(false)
        toast.success("Payment successful!")
      } else if (result.status === "expired") {
        setIsPolling(false)
        toast.error("Order has expired")
      }
    } catch (error) {
    }
  }, [qrData, onSuccess])

  // Calculate time left
  useEffect(() => {
    if (!qrData?.expires_at) return
    
    const updateTimeLeft = () => {
      const expiresAt = new Date(qrData.expires_at).getTime()
      const now = Date.now()
      const diff = Math.max(0, Math.floor((expiresAt - now) / 1000))
      setTimeLeft(diff)
      
      if (diff === 0) {
        setIsPolling(false)
      }
    }
    
    updateTimeLeft()
    const interval = setInterval(updateTimeLeft, 1000)
    return () => clearInterval(interval)
  }, [qrData?.expires_at])

  // Poll for payment status every 5 seconds
  useEffect(() => {
    if (!open || !qrData || status?.status === "paid" || status?.status === "expired") {
      setIsPolling(false)
      return
    }
    
    setIsPolling(true)
    const interval = setInterval(checkPaymentStatus, 5000)
    
    // Initial check
    checkPaymentStatus()
    
    return () => {
      clearInterval(interval)
      setIsPolling(false)
    }
  }, [open, qrData, status?.status, checkPaymentStatus])

  const handleCancel = async () => {
    if (qrData) {
      try {
        await sepayApi.cancelPayment(qrData.order_id)
      } catch (error) {
      }
    }
    onCancel()
  }

  const copyTransactionCode = () => {
    if (qrData?.transaction_code) {
      navigator.clipboard.writeText(qrData.transaction_code)
      toast.success("Transaction code copied")
    }
  }

  const formatTimeLeft = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  if (!qrData) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center">Online Payment</DialogTitle>
          <DialogDescription className="text-center">
            Scan QR code with your banking app to pay
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-4 py-4">
          {/* QR Code */}
          <div className="relative">
            {qrImageUrl ? (
              <img
                src={qrImageUrl}
                alt="Payment QR Code"
                className="w-64 h-64 border rounded-lg bg-white"
              />
            ) : (
              <div className="w-64 h-64 border rounded-lg bg-white flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            )}
            {status?.status === "paid" && (
              <div className="absolute inset-0 bg-green-500/90 flex items-center justify-center rounded-lg">
                <CheckCircle className="w-16 h-16 text-white" />
              </div>
            )}
            {status?.status === "expired" && (
              <div className="absolute inset-0 bg-red-500/90 flex items-center justify-center rounded-lg">
                <XCircle className="w-16 h-16 text-white" />
              </div>
            )}
          </div>

          {/* Amount */}
          <div className="text-center">
            <p className="text-2xl font-bold text-primary">
              {formatPrice(qrData.amount)}
            </p>
            <p className="text-sm text-muted-foreground">{qrData.description}</p>
          </div>

          {/* Transaction Code */}
          <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
            <span className="text-sm font-mono">{qrData.transaction_code}</span>
            <Button variant="ghost" size="icon" onClick={copyTransactionCode}>
              <Copy className="w-4 h-4" />
            </Button>
          </div>

          {/* Status */}
          <div className="flex items-center gap-2 text-sm">
            {isPolling && status?.status === "pending" && (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                <span className="text-muted-foreground">Waiting for payment...</span>
              </>
            )}
            {status?.status === "paid" && (
              <>
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-green-500">Payment successful!</span>
              </>
            )}
            {status?.status === "expired" && (
              <>
                <XCircle className="w-4 h-4 text-destructive" />
                <span className="text-destructive">Order has expired</span>
              </>
            )}
          </div>

          {/* Time left */}
          {status?.status === "pending" && timeLeft > 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>Time left: {formatTimeLeft(timeLeft)}</span>
            </div>
          )}

          {/* Instructions */}
          <div className="text-xs text-muted-foreground text-center space-y-1">
            <p>1. Open your banking app and scan the QR code</p>
            <p>2. Verify the amount and transfer details</p>
            <p>3. Confirm payment</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {status?.status === "pending" && (
            <>
              <Button variant="outline" className="flex-1" onClick={handleCancel}>
                Cancel
              </Button>
              <Button variant="outline" className="flex-1" onClick={checkPaymentStatus}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Check
              </Button>
            </>
          )}
          {status?.status === "paid" && (
            <Button className="w-full" onClick={onSuccess}>
              Close
            </Button>
          )}
          {status?.status === "expired" && (
            <Button variant="outline" className="w-full" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
