import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useInvoice } from "@/queries/payments"
import { Loader2, Receipt, Calendar, CreditCard, Package, Hash } from "lucide-react"
import { format } from "date-fns"

interface InvoiceDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string | null
}

export function InvoiceDetailDialog({
  open,
  onOpenChange,
  orderId
}: InvoiceDetailDialogProps) {
  const { data: invoiceData, isLoading } = useInvoice(orderId, { enabled: open && !!orderId })

  const formatCurrency = (amount: number, currency: string) => {
    if (currency === 'VND') {
      return `${amount.toLocaleString('vi-VN')} ₫`
    }
    return `$${amount.toLocaleString('en-US')}`
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'dd/MM/yyyy HH:mm:ss')
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'text-green-500'
      case 'PENDING':
        return 'text-yellow-500'
      case 'FAILED':
      case 'CANCELED':
        return 'text-red-500'
      default:
        return 'text-muted-foreground'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'Đã thanh toán'
      case 'PENDING':
        return 'Chờ thanh toán'
      case 'FAILED':
        return 'Thất bại'
      case 'CANCELED':
        return 'Đã hủy'
      default:
        return status
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Receipt className="h-6 w-6 text-primary" />
            Chi tiết hóa đơn
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : invoiceData ? (
          <div className="space-y-6">
            {/* Invoice Header */}
            <div className="bg-muted rounded-lg p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Số hóa đơn</p>
                  <p className="text-lg font-semibold font-mono">{invoiceData.invoice.invoice_number}</p>
                </div>
                <div className={`text-right ${getStatusColor(invoiceData.order.status)}`}>
                  <p className="text-sm text-muted-foreground">Trạng thái</p>
                  <p className="text-lg font-semibold">{getStatusText(invoiceData.order.status)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Ngày tạo
                  </p>
                  <p className="font-medium">{formatDate(invoiceData.order.created_at)}</p>
                </div>
                {invoiceData.order.paid_at && (
                  <div>
                    <p className="text-sm text-muted-foreground flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      Ngày thanh toán
                    </p>
                    <p className="font-medium">{formatDate(invoiceData.order.paid_at)}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Billing Info */}
            <div className="space-y-3">
              <h3 className="font-semibold text-lg">Thông tin khách hàng</h3>
              <div className="bg-muted rounded-lg p-4 space-y-2">
                <div>
                  <p className="text-sm text-muted-foreground">Tên</p>
                  <p className="font-medium">{invoiceData.invoice.billing_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Địa chỉ</p>
                  <p className="font-medium">{invoiceData.invoice.billing_address}</p>
                </div>
              </div>
            </div>

            {/* Plan Details */}
            {invoiceData.plan && (
              <div className="space-y-3">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Chi tiết gói dịch vụ
                </h3>
                <div className="bg-muted rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Tên gói</span>
                    <span className="font-semibold">{invoiceData.plan.name}</span>
                  </div>
                  {invoiceData.plan.description && (
                    <div className="flex items-start justify-between">
                      <span className="text-muted-foreground">Mô tả</span>
                      <span className="font-medium text-right max-w-xs">{invoiceData.plan.description}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Chu kỳ</span>
                    <span className="font-medium capitalize">
                      {invoiceData.order.billing_cycle === 'monthly' ? 'Hàng tháng' : 'Hàng năm'}
                    </span>
                  </div>
                  {invoiceData.plan.monthly_credits !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Credits / tháng</span>
                      <span className="font-medium">
                        {invoiceData.plan.monthly_credits === -1 ? 'Không giới hạn' : invoiceData.plan.monthly_credits.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {invoiceData.plan.available_project !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Số dự án</span>
                      <span className="font-medium">
                        {invoiceData.plan.available_project === -1 ? 'Không giới hạn' : invoiceData.plan.available_project}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Payment Details */}
            {/* <div className="space-y-3">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Thông tin thanh toán
              </h3>
              <div className="bg-muted rounded-lg p-4 space-y-3">
                {invoiceData.order.sepay_transaction_code && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground flex items-center gap-2">
                      <Hash className="h-4 w-4" />
                      Mã đơn hàng
                    </span>
                    <span className="font-mono font-medium">{invoiceData.order.sepay_transaction_code}</span>
                  </div>
                )}
                {invoiceData.order.payos_transaction_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Mã giao dịch</span>
                    <span className="font-mono font-medium text-sm">{invoiceData.order.payos_transaction_id}</span>
                  </div>
                )}
              </div>
            </div> */}

            {/* Total Amount */}
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">Tổng thanh toán</span>
                <span className="text-3xl font-bold text-primary">
                  {formatCurrency(invoiceData.invoice.amount, invoiceData.invoice.currency)}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            Không tìm thấy thông tin hóa đơn
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
