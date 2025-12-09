import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2, Receipt, Coins } from "lucide-react"

interface CreditPurchaseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  creditAmount: number
  pricePerCredit: number
  totalPrice: string
  currency: string
  onConfirm: () => void
  isProcessing: boolean
}

export function CreditPurchaseDialog({
  open,
  onOpenChange,
  creditAmount,
  pricePerCredit,
  totalPrice,
  currency,
  onConfirm,
  isProcessing
}: CreditPurchaseDialogProps) {
  const formatPrice = (amount: number | string, curr: string) => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
    if (curr === 'VND') {
      return `${numAmount.toLocaleString('vi-VN')} ₫`
    }
    return `$${numAmount.toFixed(2)}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5 text-primary" />
            Xác nhận mua credits
          </DialogTitle>
          <DialogDescription>
            Vui lòng kiểm tra thông tin trước khi thanh toán
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Credit Info */}
          <div className="bg-muted rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 mb-2">
              <Coins className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Chi tiết mua credits</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Số lượng credits</span>
              <span className="font-semibold">{creditAmount.toLocaleString()} credits</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Giá mỗi credit</span>
              <span className="font-medium">{formatPrice(pricePerCredit, currency)}</span>
            </div>
          </div>

          {/* Total Amount */}
          <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold">Tổng thanh toán</span>
              <span className="text-2xl font-bold text-primary">
                {formatPrice(totalPrice, currency)}
              </span>
            </div>
          </div>

          {/* Info Note */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <p className="text-xs text-blue-600 dark:text-blue-400">
              Credits sẽ được thêm vào tài khoản ngay sau khi thanh toán thành công. Credits không có thời hạn sử dụng.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isProcessing}
            className="flex-1"
          >
            Hủy
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isProcessing}
            className="flex-1"
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Đang xử lý...
              </>
            ) : (
              'Thanh toán'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
