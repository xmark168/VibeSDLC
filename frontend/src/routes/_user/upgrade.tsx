import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useState, useEffect } from "react"
import { Info, RefreshCw, Layers, Zap, Receipt, XCircle, CheckCircle, Clock, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeaderProject } from "@/components/projects/header"
import { usePlans } from "@/queries/plans"
import { formatPrice } from "@/apis/plans"
import { InvoiceConfirmDialog } from "@/components/upgrade/InvoiceConfirmDialog"
import { InvoiceDetailDialog } from "@/components/upgrade/InvoiceDetailDialog"
import { useCreatePaymentLink, usePaymentHistory } from "@/queries/payments"
import { paymentsApi } from "@/apis/payments"
import type { Plan } from "@/types/plan"
import toast from "react-hot-toast"

export const Route = createFileRoute('/_user/upgrade')({
  component: RouteComponent,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      status: (search.status as string) || undefined,
      orderCode: (search.orderCode as string) || undefined,
    }
  },
})

type BillingTab = "plan" | "credit" | "history"

function RouteComponent() {
  const navigate = useNavigate()
  const searchParams = useSearch({ from: '/_user/upgrade' })
  const [billingTab, setBillingTab] = useState<BillingTab>("plan")
  const [creditAmount, setCreditAmount] = useState<number>(100)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly')

  // Fetch active plans from API
  const { data: plansData, isLoading: plansLoading } = usePlans({
    is_active: true,
    order_by: 'sort_index',
    limit: 100
  })

  const plans = plansData?.data || []

  // Invoice confirm dialog state
  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const createPayment = useCreatePaymentLink()

  // Invoice detail dialog state
  const [invoiceDetailOpen, setInvoiceDetailOpen] = useState(false)
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // Fetch payment history with pagination
  const { data: paymentHistory, isLoading: historyLoading } = usePaymentHistory({
    limit: itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage
  })

  // Calculate total pages
  const totalPages = paymentHistory ? Math.ceil(paymentHistory.total / itemsPerPage) : 0

  // Reset page when switching to history tab
  useEffect(() => {
    if (billingTab === 'history') {
      setCurrentPage(1)
    }
  }, [billingTab])

  // Check payment status from URL params when component mounts
  useEffect(() => {
    console.log('Search params:', searchParams)

    // Check if we just returned from payment
    if (searchParams.status) {
      const status = searchParams.status.toLowerCase()
      console.log('Payment status detected:', status)

      // Check if already processed to avoid loop
      const processed = sessionStorage.getItem('payment_processed')
      if (processed === searchParams.orderCode) {
        console.log('Payment already processed, skipping')
        return
      }

      // Mark as processed
      if (searchParams.orderCode) {
        sessionStorage.setItem('payment_processed', searchParams.orderCode)
      }

      // Normalize PayOS status (PAID/CANCELLED) to our format
      let normalizedStatus = 'unknown'
      if (status === 'paid' || status === 'success') {
        normalizedStatus = 'success'
      } else if (status === 'cancelled' || status === 'cancel') {
        normalizedStatus = 'cancel'
      }

      // Save payment status and orderCode to localStorage
      localStorage.setItem('payment_status', normalizedStatus)
      if (searchParams.orderCode) {
        localStorage.setItem('payment_order_code', searchParams.orderCode)
      }

      // Clear URL params and reload
      window.location.href = '/upgrade'
      return
    }

    // Check localStorage for payment status after reload
    const paymentStatus = localStorage.getItem('payment_status')
    const orderCode = localStorage.getItem('payment_order_code')

    if (paymentStatus) {
      console.log('Processing payment status:', paymentStatus, 'Order Code:', orderCode)

      // Clear localStorage first
      localStorage.removeItem('payment_status')
      localStorage.removeItem('payment_order_code')
      sessionStorage.removeItem('payment_processed')

      // If successful payment, sync order status first
      if (paymentStatus === 'success' && orderCode) {
        const loadingToast = toast.loading('Đang xác nhận thanh toán...', {
          style: {
            background: '#1e293b',
            color: '#fff',
            border: '1px solid #334155',
          },
        })

        // Call sync endpoint to update order and activate subscription
        paymentsApi.syncPaymentStatusByCode(parseInt(orderCode))
          .then((response) => {
            toast.dismiss(loadingToast)
            console.log('Sync response:', response)

            if (response.status === 'PAID') {
              toast.success('Thanh toán thành công!\nGói dịch vụ của bạn đã được kích hoạt', {
                duration: 5000,
                style: {
                  background: '#1e293b',
                  color: '#fff',
                  border: '1px solid #334155',
                  padding: '16px',
                },
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              })
            } else {
              toast('Thanh toán đang được xử lý\nVui lòng kiểm tra lại sau ít phút', {
                duration: 5000,
                icon: '⏳',
                style: {
                  background: '#1e293b',
                  color: '#fff',
                  border: '1px solid #334155',
                  padding: '16px',
                },
              })
            }
          })
          .catch((error) => {
            toast.dismiss(loadingToast)
            console.error('Failed to sync payment status:', error)
            toast.error('Không thể xác nhận thanh toán\nVui lòng kiểm tra lịch sử giao dịch', {
              duration: 5000,
              style: {
                background: '#1e293b',
                color: '#fff',
                border: '1px solid #334155',
                padding: '16px',
              },
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            })
          })
      } else if (paymentStatus === 'cancel') {
        // Show cancel notification
        toast.error('Thanh toán đã bị hủy\nBạn có thể thử lại bất cứ lúc nào', {
          duration: 4000,
          style: {
            background: '#1e293b',
            color: '#fff',
            border: '1px solid #334155',
            padding: '16px',
          },
          iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
          },
        })
      }
    }
  }, [searchParams])

  // Handle upgrade button click - show invoice confirmation
  const handleUpgradeClick = (plan: Plan) => {
    setSelectedPlan(plan)
    setInvoiceDialogOpen(true)
  }

  // Handle payment confirmation - create order and redirect to PayOS
  const handlePaymentConfirm = async () => {
    if (!selectedPlan) return

    try {
      const paymentData = await createPayment.mutateAsync({
        plan_id: selectedPlan.id,
        billing_cycle: billingCycle,
      })

      // Close dialog
      setInvoiceDialogOpen(false)

      // Show loading message
      const loadingToast = toast.loading("Đang chuyển đến trang thanh toán...", {
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })

      // Redirect to PayOS checkout page (same window)
      setTimeout(() => {
        toast.dismiss(loadingToast)
        window.location.href = paymentData.checkout_url
      }, 1000)
    } catch (error) {
      // Error is handled by the mutation hook
      console.error('Payment creation failed:', error)
      toast.error('Có lỗi xảy ra khi tạo thanh toán', {
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })
    }
  }

  // Handle click on payment history item
  const handleHistoryClick = (orderId: string) => {
    setSelectedOrderId(orderId)
    setInvoiceDetailOpen(true)
  }

  // Get current plan info (assuming FREE for now - TODO: Get from user subscription)
  const currentPlanCode = "FREE"
  const currentPlan = plans.find(p => p.code === currentPlanCode)

  const getPricePerCredit = () => {
    if (!currentPlan || !currentPlan.additional_credit_price) return 0
    return currentPlan.additional_credit_price / 100 // Price per credit
  }

  const totalPrice = (creditAmount * getPricePerCredit()).toFixed(2)

  return (
    <div className="min-h-screen bg-background">
      <HeaderProject />

      <div className="container mx-auto px-4 py-8 max-w-6xl">

        {/* Tabs */}
        <div className="border-b mb-8">
          <div className="flex gap-6">
            <button
              onClick={() => setBillingTab("plan")}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                billingTab === "plan"
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Plan
            </button>
            <button
              onClick={() => setBillingTab("credit")}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                billingTab === "credit"
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Credit
            </button>
            <button
              onClick={() => setBillingTab("history")}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                billingTab === "history"
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              History
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {billingTab === "plan" && (
          <div className="py-6">
            {/* Billing Cycle Toggle */}
            <div className="flex justify-center mb-8">
              <div className="inline-flex items-center gap-4 bg-secondary/30 rounded-full p-1.5">
                <button
                  onClick={() => setBillingCycle('monthly')}
                  className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-200 ${
                    billingCycle === 'monthly'
                      ? 'bg-primary text-primary-foreground shadow-lg'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingCycle('yearly')}
                  className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-200 relative ${
                    billingCycle === 'yearly'
                      ? 'bg-primary text-primary-foreground shadow-lg'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Yearly
                  <span className="ml-2 text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
                    Save up to 20%
                  </span>
                </button>
              </div>
            </div>

            {plansLoading ? (
              <div className="text-center py-12 text-muted-foreground">
                Loading plans...
              </div>
            ) : plans.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No plans available
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {plans.map((plan, index) => {
                  // Check if this is user's current plan (for now, assume Free is current)
                  const isCurrentPlan = plan.code === 'FREE'

                  return (
                    <div
                      key={plan.id}
                      className={`bg-secondary/20 rounded-lg p-6 border flex flex-col ${
                        plan.is_featured ? 'ring-2 ring-primary' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xl font-semibold">{plan.name}</h4>
                        {plan.is_featured && (
                          <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded">
                            Popular
                          </span>
                        )}
                      </div>

                      {plan.description && (
                        <p className="text-sm text-muted-foreground mb-4">
                          {plan.description}
                        </p>
                      )}

                      <div className="mb-6">
                        {plan.is_custom_price ? (
                          <span className="text-4xl font-bold">Custom</span>
                        ) : (
                          <>
                            <div className="flex items-baseline gap-2">
                              <span className="text-4xl font-bold">
                                {billingCycle === 'monthly'
                                  ? formatPrice(plan.monthly_price || 0, plan.currency)
                                  : formatPrice(plan.yearly_price || 0, plan.currency)
                                }
                              </span>
                              <span className="text-muted-foreground">
                                / {billingCycle === 'monthly' ? 'month' : 'year'}
                              </span>
                            </div>
                            {billingCycle === 'yearly' && plan.yearly_discount_percentage && plan.yearly_discount_percentage > 0 && (
                              <p className="text-sm text-green-400 mt-1">
                                Save {plan.yearly_discount_percentage}% with yearly billing
                              </p>
                            )}
                          </>
                        )}
                      </div>

                      <Button
                        disabled={isCurrentPlan}
                        onClick={() => !isCurrentPlan && handleUpgradeClick(plan)}
                        className={`w-full mb-6 ${
                          isCurrentPlan
                            ? 'bg-secondary text-foreground hover:bg-secondary cursor-not-allowed'
                            : 'bg-primary hover:bg-primary/90'
                        }`}
                      >
                        {isCurrentPlan ? 'Your current plan' : 'Upgrade'}
                      </Button>

                      {/* Features */}
                      <div className="space-y-3">
                        {plan.monthly_credits !== null && (
                          <div className="flex items-center gap-2 text-sm">
                            <RefreshCw className="h-4 w-4 text-muted-foreground" />
                            <span>
                              <strong>{plan.monthly_credits === -1 ? 'Unlimited' : plan.monthly_credits}</strong> credits / month
                            </span>
                          </div>
                        )}

                        {plan.available_project !== null && (
                          <div className="flex items-center gap-2 text-sm">
                            <Layers className="h-4 w-4 text-muted-foreground" />
                            <span>
                              <strong>{plan.available_project === -1 ? 'Unlimited' : plan.available_project}</strong> project
                            </span>
                          </div>
                        )}

                        {plan.additional_credit_price !== null && (
                          <div className="flex items-center gap-2 text-sm">
                            <Zap className="h-4 w-4 text-muted-foreground" />
                            <span>
                              <span className="font-semibold">
                                {formatPrice(plan.additional_credit_price, plan.currency)}
                              </span> / 100 credits
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {billingTab === "credit" && (
          <div className="py-6 flex justify-center">
            <div className="max-w-xl w-full">
              {/* Plan Info Card */}
              <div className="bg-secondary/30 rounded-lg p-6 mb-8">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold">Purchase Credits</h3>
                  {currentPlan && (
                    <span className="text-sm px-3 py-1 bg-secondary rounded-md">
                      {currentPlan.name}
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  Your plan rate: <span className="font-semibold text-foreground">
                    {currentPlan?.additional_credit_price ? formatPrice(currentPlan.additional_credit_price, currentPlan.currency) : '—'}
                  </span> per 100 credits
                </p>
              </div>

              {/* Credit Amount Selection */}
              <div className="space-y-6">
                <div>
                  <label className="text-sm font-medium mb-3 block">
                    Select credit amount (minimum 10 credits)
                  </label>

                  {/* Input Field */}
                  <div className="flex items-center gap-4 mb-4">
                    <input
                      type="number"
                      min="10"
                      step="10"
                      value={creditAmount}
                      onChange={(e) => {
                        const val = parseInt(e.target.value) || 10
                        setCreditAmount(Math.max(10, val))
                      }}
                      className="flex h-12 w-full rounded-lg border border-input bg-background px-4 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    <span className="text-sm text-muted-foreground whitespace-nowrap">credits</span>
                  </div>

                  {/* Slider */}
                  <input
                    type="range"
                    min="10"
                    max="1000"
                    step="10"
                    value={creditAmount}
                    onChange={(e) => setCreditAmount(parseInt(e.target.value))}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />

                  {/* Quick Select Buttons */}
                  <div className="flex gap-2 mt-4">
                    {[100, 250, 500, 1000].map((amount) => (
                      <button
                        key={amount}
                        onClick={() => setCreditAmount(amount)}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          creditAmount === amount
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary hover:bg-secondary/80"
                        }`}
                      >
                        {amount}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Price Breakdown */}
                <div className="bg-secondary/20 rounded-lg p-6 space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Credits</span>
                    <span className="font-medium">{creditAmount} credits</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Price per credit</span>
                    <span className="font-medium">
                      {currentPlan?.currency === 'VND'
                        ? `${(getPricePerCredit()).toLocaleString('vi-VN')} ₫`
                        : `$${getPricePerCredit().toFixed(3)}`
                      }
                    </span>
                  </div>
                  <div className="border-t pt-3 flex items-center justify-between">
                    <span className="font-semibold">Total</span>
                    <span className="text-2xl font-bold">
                      {currentPlan?.currency === 'VND'
                        ? `${parseFloat(totalPrice).toLocaleString('vi-VN')} ₫`
                        : `$${totalPrice}`
                      }
                    </span>
                  </div>
                </div>

                {/* Purchase Button */}
                <Button className="w-full h-12 text-base bg-primary hover:bg-primary/90">
                  Purchase
                </Button>

                {/* Info Note */}
                <p className="text-xs text-muted-foreground text-center">
                  Credits will be added to your account immediately after purchase. No expiration date.
                </p>
              </div>
            </div>
          </div>
        )}

        {billingTab === "history" && (
          <div className="py-6">
            {historyLoading ? (
              <div className="text-center py-12 text-muted-foreground">
                Loading payment history...
              </div>
            ) : paymentHistory && paymentHistory.data.length > 0 ? (
              <div className="space-y-4">
                {/* Showing info */}
                <div className="text-sm text-slate-400">
                  Showing {paymentHistory.offset + 1} - {Math.min(paymentHistory.offset + paymentHistory.limit, paymentHistory.total)} of {paymentHistory.total} transactions
                </div>

                {paymentHistory.data.map((order) => {
                  const getStatusDisplay = () => {
                    switch (order.status) {
                      case 'PAID':
                        return { icon: CheckCircle, text: 'Completed', color: 'text-green-500' }
                      case 'PENDING':
                        return { icon: Clock, text: 'Pending', color: 'text-yellow-500' }
                      case 'FAILED':
                      case 'CANCELED':
                        return { icon: XCircle, text: 'Expired', color: 'text-destructive' }
                      default:
                        return { icon: Clock, text: order.status, color: 'text-slate-400' }
                    }
                  }

                  const statusDisplay = getStatusDisplay()
                  const StatusIcon = statusDisplay.icon

                  const getTitle = () => {
                    if (order.plan_code && order.billing_cycle) {
                      const cycle = order.billing_cycle === 'monthly' ? 'Monthly' : 'Yearly'
                      return `${order.plan_code} Plan - ${cycle}`
                    }
                    return 'Purchase'
                  }

                  const formatDate = (dateString: string) => {
                    try {
                      return new Date(dateString).toLocaleString('vi-VN')
                    } catch {
                      return dateString
                    }
                  }

                  const formatAmount = (amount: number) => {
                    return `${amount.toLocaleString('vi-VN')} ₫`
                  }

                  return (
                    <div
                      key={order.id}
                      onClick={() => handleHistoryClick(order.id)}
                      className="bg-secondary/20 rounded-lg p-6 space-y-4 cursor-pointer hover:bg-secondary/30 transition-colors"
                    >
                      {/* Header with ID and Status */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Receipt className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-mono text-muted-foreground">
                            {order.id.slice(0, 8)}...{order.id.slice(-8)}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              navigator.clipboard.writeText(order.id)
                              toast.success('Copied to clipboard')
                            }}
                            className="text-primary hover:text-primary/80 text-sm font-medium transition-colors"
                          >
                            Copy
                          </button>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusIcon className={`h-4 w-4 ${statusDisplay.color}`} />
                          <span className={`text-sm font-medium ${statusDisplay.color}`}>
                            {statusDisplay.text}
                          </span>
                        </div>
                      </div>

                      {/* Payment Details and Timestamps */}
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <h4 className="font-semibold">{getTitle()}</h4>
                          <p className="text-sm text-muted-foreground">{formatAmount(order.amount)}</p>
                        </div>
                        <div className="space-y-1 text-right">
                          <p className="text-sm text-muted-foreground">
                            Created at: {formatDate(order.created_at)}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Paid at: {order.paid_at ? formatDate(order.paid_at) : '—'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-6">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="h-5 w-5" />
                    </button>

                    <div className="flex items-center gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                        // Show first page, last page, current page, and pages around current
                        const showPage =
                          page === 1 ||
                          page === totalPages ||
                          Math.abs(page - currentPage) <= 1

                        if (!showPage) {
                          // Show ellipsis
                          if (page === currentPage - 2 || page === currentPage + 2) {
                            return <span key={page} className="px-2 text-slate-500">...</span>
                          }
                          return null
                        }

                        return (
                          <button
                            key={page}
                            onClick={() => setCurrentPage(page)}
                            className={`min-w-[40px] h-10 px-3 rounded-lg font-medium transition-colors ${
                              currentPage === page
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary hover:bg-secondary/80'
                            }`}
                          >
                            {page}
                          </button>
                        )
                      })}
                    </div>

                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                No payment history found
              </div>
            )}
          </div>
        )}
      </div>

      {/* Invoice Confirmation Dialog */}
      <InvoiceConfirmDialog
        open={invoiceDialogOpen}
        onOpenChange={setInvoiceDialogOpen}
        plan={selectedPlan}
        billingCycle={billingCycle}
        onConfirm={handlePaymentConfirm}
        isProcessing={createPayment.isPending}
      />

      {/* Invoice Detail Dialog */}
      <InvoiceDetailDialog
        open={invoiceDetailOpen}
        onOpenChange={setInvoiceDetailOpen}
        orderId={selectedOrderId}
      />
    </div>
  )
}
