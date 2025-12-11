import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2, Receipt, Calendar, CreditCard, Coins } from "lucide-react"
import type { Plan } from "@/types/plan"

interface InvoiceConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  plan: Plan | null
  billingCycle: 'monthly' | 'yearly'
  onConfirm: () => void
  isProcessing: boolean
  isPurchasingCredit?: boolean
}

export function InvoiceConfirmDialog({
  open,
  onOpenChange,
  plan,
  billingCycle,
  onConfirm,
  isProcessing,
  isPurchasingCredit = false
}: InvoiceConfirmDialogProps) {
  if (!plan) return null

  const amount = billingCycle === 'monthly' ? plan.monthly_price : plan.yearly_price
  const period = billingCycle === 'monthly' ? '1 tháng' : '1 năm'
  const discount = !isPurchasingCredit && billingCycle === 'yearly' && plan.yearly_discount_percentage
    ? plan.yearly_discount_percentage
    : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isPurchasingCredit ? (
              <Coins className="h-5 w-5 text-primary" />
            ) : (
              <Receipt className="h-5 w-5 text-primary" />
            )}
            {isPurchasingCredit ? 'Xác nhận mua credits' : 'Xác nhận hóa đơn'}
          </DialogTitle>
          <DialogDescription>
            Vui lòng kiểm tra thông tin trước khi thanh toán
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Plan/Credit Info */}
          <div className="bg-muted rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {isPurchasingCredit ? 'Mua credits' : 'Gói dịch vụ'}
              </span>
              <span className="font-semibold">{plan.name}</span>
            </div>

            {plan.description && (
              <p className="text-xs text-muted-foreground">{plan.description}</p>
            )}
          </div>

          {/* Billing Details */}
          <div className="space-y-3">
            {!isPurchasingCredit && (
              <>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Chu kỳ thanh toán
                  </span>
                  <span className="font-medium capitalize">
                    {billingCycle === 'monthly' ? 'Hàng tháng' : 'Hàng năm'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Thời hạn sử dụng</span>
                  <span className="font-medium">{period}</span>
                </div>
              </>
            )}

            {isPurchasingCredit && plan.monthly_credits !== null && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Số lượng credits</span>
                <span className="font-medium">
                  {plan.monthly_credits.toLocaleString()} credits
                </span>
              </div>
            )}

            {!isPurchasingCredit && plan.monthly_credits !== null && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Credits / tháng</span>
                <span className="font-medium">
                  {plan.monthly_credits === -1 ? 'Không giới hạn' : plan.monthly_credits.toLocaleString()}
                </span>
              </div>
            )}

            {!isPurchasingCredit && plan.available_project !== null && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Số dự án</span>
                <span className="font-medium">
                  {plan.available_project === -1 ? 'Không giới hạn' : plan.available_project}
                </span>
              </div>
            )}
          </div>

          {/* Price Summary */}
          <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 space-y-3">
            {discount > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Giá gốc</span>
                <span className="text-muted-foreground line-through">
                  {plan.monthly_price
                    ? new Intl.NumberFormat('vi-VN', {
                        style: 'currency',
                        currency: plan.currency
                      }).format((plan.monthly_price || 0) * (billingCycle === 'yearly' ? 12 : 1))
                    : '0'}
                </span>
              </div>
            )}

            {discount > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-green-600">Giảm giá ({discount}%)</span>
                <span className="text-green-600 font-medium">
                  -{new Intl.NumberFormat('vi-VN', {
                    style: 'currency',
                    currency: plan.currency
                  }).format(((plan.monthly_price || 0) * 12) - (amount || 0))}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="font-semibold">Tổng thanh toán</span>
              <span className="text-2xl font-bold text-primary">
                {new Intl.NumberFormat('vi-VN', {
                  style: 'currency',
                  currency: plan.currency
                }).format(amount || 0)}
              </span>
            </div>
          </div>

          {/* Notice */}
          <p className="text-xs text-center text-muted-foreground">
            {isPurchasingCredit 
              ? 'Credits sẽ được thêm vào tài khoản ngay sau khi thanh toán thành công'
              : 'Sau khi thanh toán, gói dịch vụ sẽ được kích hoạt tự động'
            }
          </p>
        </div>

        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isProcessing}
            className="flex-1"
          >
            Hủy
          </Button>
          <Button
            onClick={() => onConfirm()}
            disabled={isProcessing}
            className="flex-1"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Đang xử lý...
              </>
            ) : (
              <>
                <CreditCard className="w-4 h-4 mr-2" />
                Thanh toán
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
