import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useState, useEffect } from "react"
import { Check, Sparkles, Zap, Crown, ChevronLeft, ChevronRight, Receipt, CheckCircle, XCircle, Clock, CreditCard, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeaderProject } from "@/components/projects/header"
import { usePlans } from "@/queries/plans"
import { formatPrice } from "@/apis/plans"
import { InvoiceConfirmDialog } from "@/components/upgrade/InvoiceConfirmDialog"
import { InvoiceDetailDialog } from "@/components/upgrade/InvoiceDetailDialog"
import { SePayQRDialog } from "@/components/upgrade/SePayQRDialog"
import { useCreatePaymentLink, usePaymentHistory } from "@/queries/payments"
import { paymentsApi } from "@/apis/payments"
import { sepayApi } from "@/apis/sepay"
import { useCurrentSubscription } from "@/queries/subscription"
import type { Plan } from "@/types/plan"
import type { SePayQRResponse } from "@/types/sepay"
import toast from "react-hot-toast"
import { useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"

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
  const queryClient = useQueryClient()
  const [billingTab, setBillingTab] = useState<BillingTab>("plan")
  const [creditAmount, setCreditAmount] = useState<number>(100)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly')

  const { data: plansData, isLoading: plansLoading } = usePlans({
    is_active: true,
    order_by: 'sort_index',
    limit: 100
  })

  const plans = plansData?.data || []
  const { data: subscriptionData } = useCurrentSubscription()

  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [isPurchasingCredit, setIsPurchasingCredit] = useState(false)
  const [isProcessingPayment, setIsProcessingPayment] = useState(false)
  const createPayment = useCreatePaymentLink()

  const [invoiceDetailOpen, setInvoiceDetailOpen] = useState(false)
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)

  const [sepayDialogOpen, setSepayDialogOpen] = useState(false)
  const [sepayQRData, setSepayQRData] = useState<SePayQRResponse | null>(null)

  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const { data: paymentHistory, isLoading: historyLoading } = usePaymentHistory({
    limit: itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage
  })

  const totalPages = paymentHistory ? Math.ceil(paymentHistory.total / itemsPerPage) : 0

  useEffect(() => {
    if (billingTab === 'history') {
      setCurrentPage(1)
    }
  }, [billingTab])

  useEffect(() => {
    if (searchParams.status) {
      const status = searchParams.status.toLowerCase()
      const processed = sessionStorage.getItem('payment_processed')
      if (processed === searchParams.orderCode) return

      if (searchParams.orderCode) {
        sessionStorage.setItem('payment_processed', searchParams.orderCode)
      }

      let normalizedStatus = 'unknown'
      if (status === 'paid' || status === 'success') {
        normalizedStatus = 'success'
      } else if (status === 'cancelled' || status === 'cancel') {
        normalizedStatus = 'cancel'
      }

      localStorage.setItem('payment_status', normalizedStatus)
      if (searchParams.orderCode) {
        localStorage.setItem('payment_order_code', searchParams.orderCode)
      }

      window.location.href = '/upgrade'
      return
    }

    const paymentStatus = localStorage.getItem('payment_status')
    const orderCode = localStorage.getItem('payment_order_code')

    if (paymentStatus) {
      localStorage.removeItem('payment_status')
      localStorage.removeItem('payment_order_code')
      sessionStorage.removeItem('payment_processed')

      if (paymentStatus === 'success' && orderCode) {
        const loadingToast = toast.loading('Confirming payment...')

        paymentsApi.syncPaymentStatusByCode(parseInt(orderCode))
          .then((response) => {
            toast.dismiss(loadingToast)
            if (response.status === 'PAID') {
              queryClient.invalidateQueries({ queryKey: ['subscription', 'current'] })
              toast.success('Payment successful! Your subscription has been activated', { duration: 5000 })
            } else {
              toast('Payment is being processed. Please check again in a few minutes', { duration: 5000, icon: '⏳' })
            }
          })
          .catch(() => {
            toast.dismiss(loadingToast)
            toast.error('Unable to confirm payment. Please check transaction history', { duration: 5000 })
          })
      } else if (paymentStatus === 'cancel') {
        toast.error('Payment was cancelled. You can try again anytime', { duration: 4000 })
      }
    }
  }, [searchParams, queryClient])

  const handleUpgradeClick = (plan: Plan) => {
    setSelectedPlan(plan)
    setIsPurchasingCredit(false)
    setInvoiceDialogOpen(true)
  }

  const handleCreditPurchaseClick = () => {
    // Create a fake plan for credit purchase display
    const creditPlan: Plan = {
      id: 'credit-purchase',
      code: 'CREDIT',
      name: `${creditAmount} Credits`,
      description: `Purchase ${creditAmount} additional credits`,
      tier: 'pay',
      monthly_price: parseFloat(totalPrice),
      yearly_price: null,
      currency: currentPlan?.currency || 'VND',
      monthly_credits: creditAmount,
      available_project: null,
      additional_credit_price: currentPlan?.additional_credit_price || 0,
      yearly_discount_percentage: null,
      is_active: true,
      is_featured: false,
      is_custom_price: false,
      sort_index: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    setSelectedPlan(creditPlan)
    setIsPurchasingCredit(true)
    setInvoiceDialogOpen(true)
  }

  const handlePaymentConfirm = async () => {
    if (!selectedPlan) return

    setIsProcessingPayment(true)

    try {
      let qrData: SePayQRResponse

      if (isPurchasingCredit) {
        // Credit purchase
        qrData = await sepayApi.createCreditPurchase({
          credit_amount: creditAmount,
        })
      } else {
        // Plan purchase
        qrData = await sepayApi.createPayment({
          plan_id: selectedPlan.id,
          billing_cycle: billingCycle,
          auto_renew: false,
        })
      }

      setInvoiceDialogOpen(false)
      setSepayQRData(qrData)
      setSepayDialogOpen(true)
    } catch (error: any) {
      toast.error(error?.body?.detail || 'An error occurred while creating payment')
    } finally {
      setIsProcessingPayment(false)
    }
  }

  const handleSepaySuccess = () => {
    setSepayDialogOpen(false)
    setSepayQRData(null)
    queryClient.invalidateQueries({ queryKey: ['subscription', 'current'] })
    queryClient.invalidateQueries({ queryKey: ['payments', 'history'] })
  }

  const handleSepayCancel = () => {
    setSepayDialogOpen(false)
    setSepayQRData(null)
  }

  const handleHistoryClick = (orderId: string) => {
    setSelectedOrderId(orderId)
    setInvoiceDetailOpen(true)
  }

  const currentPlanCode = subscriptionData?.subscription?.plan?.code || "FREE"
  const currentPlan = subscriptionData?.subscription?.plan || plans.find(p => p.code === 'FREE')

  const getPricePerCredit = () => {
    if (!currentPlan || !currentPlan.additional_credit_price) return 0
    return currentPlan.additional_credit_price / 100
  }

  const totalPrice = (creditAmount * getPricePerCredit()).toFixed(2)

  const getPlanIcon = (index: number) => {
    const icons = [Sparkles, Zap, Crown]
    return icons[index] || Sparkles
  }

  return (
    <div className="min-h-screen bg-background">
      <HeaderProject />

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[128px]" />
        <div className="absolute top-20 right-1/4 w-80 h-80 bg-primary/5 rounded-full blur-[100px]" />

        <div className="relative container mx-auto px-4 pt-16 pb-8 max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-primary">Upgrade your experience</span>
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight">
              Choose Your{" "}
              <span className="text-primary">
                Perfect Plan
              </span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Unlock powerful features and take your projects to the next level with our flexible pricing options
            </p>
          </motion.div>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="flex justify-center mb-10"
          >
            <div className="inline-flex p-1.5 rounded-2xl bg-muted/50 backdrop-blur-sm border border-border">
              {[
                { id: 'plan', label: 'Plans', icon: Crown },
                { id: 'credit', label: 'Credits', icon: Zap },
                { id: 'history', label: 'History', icon: Receipt },
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setBillingTab(tab.id as BillingTab)}
                    className={`relative px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                      billingTab === tab.id
                        ? 'text-primary-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {billingTab === tab.id && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute inset-0 bg-primary rounded-xl"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                    <Icon className="w-4 h-4 relative z-10" />
                    <span className="relative z-10">{tab.label}</span>
                  </button>
                )
              })}
            </div>
          </motion.div>
        </div>
      </div>

      <div className="container mx-auto px-4 pb-20 max-w-6xl">
        {/* Plan Tab Content */}
        {billingTab === "plan" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            {/* Billing Cycle Toggle */}
            <div className="flex justify-center mb-12">
              <div className="relative inline-flex p-1 rounded-full bg-muted border border-border">
                <button
                  onClick={() => setBillingCycle('monthly')}
                  className={`relative px-8 py-3 rounded-full text-sm font-medium transition-all duration-300 ${
                    billingCycle === 'monthly'
                      ? 'text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {billingCycle === 'monthly' && (
                    <motion.div
                      layoutId="billingToggle"
                      className="absolute inset-0 bg-background rounded-full shadow-sm"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10">Monthly</span>
                </button>
                <button
                  onClick={() => setBillingCycle('yearly')}
                  className={`relative px-8 py-3 rounded-full text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                    billingCycle === 'yearly'
                      ? 'text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {billingCycle === 'yearly' && (
                    <motion.div
                      layoutId="billingToggle"
                      className="absolute inset-0 bg-background rounded-full shadow-sm"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10">Yearly</span>
                  <span className="relative z-10 text-xs px-2 py-0.5 bg-green-500/20 text-green-600 dark:text-green-400 rounded-full">
                    -20%
                  </span>
                </button>
              </div>
            </div>

            {plansLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-[500px] rounded-2xl bg-muted/50 animate-pulse" />
                ))}
              </div>
            ) : plans.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground">
                No plans available
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {plans.map((plan, index) => {
                  const isCurrentPlan = plan.code === currentPlanCode
                  const Icon = getPlanIcon(index)

                  return (
                    <motion.div
                      key={plan.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: index * 0.1 }}
                      className={`relative group ${plan.is_featured ? 'md:-mt-4 md:mb-4' : ''}`}
                    >
                      {/* Featured Badge */}
                      {plan.is_featured && (
                        <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-20">
                          <div className="px-4 py-1.5 rounded-full bg-primary text-primary-foreground text-xs font-semibold shadow-lg">
                            Most Popular
                          </div>
                        </div>
                      )}

                      <div
                        className={`relative h-full rounded-2xl overflow-hidden transition-all duration-500 ${
                          plan.is_featured
                            ? 'bg-card border-2 border-primary shadow-xl shadow-primary/10'
                            : 'bg-card border border-border hover:border-primary/50'
                        }`}
                      >
                        {/* Glow Effect on Hover */}
                        <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${
                          plan.is_featured 
                            ? 'bg-gradient-to-t from-primary/5 to-transparent' 
                            : 'bg-gradient-to-t from-muted/50 to-transparent'
                        }`} />

                        <div className="relative p-8 flex flex-col h-full">
                          {/* Plan Header */}
                          <div className="mb-6">
                            <div className={`inline-flex p-3 rounded-xl mb-4 ${
                              plan.is_featured 
                                ? 'bg-primary/10' 
                                : 'bg-muted'
                            }`}>
                              <Icon className={`w-6 h-6 ${
                                plan.is_featured ? 'text-primary' : 'text-muted-foreground'
                              }`} />
                            </div>
                            <h3 className="text-2xl font-bold text-foreground mb-2">{plan.name}</h3>
                            {plan.description && (
                              <p className="text-sm text-muted-foreground line-clamp-2">{plan.description}</p>
                            )}
                          </div>

                          {/* Price */}
                          <div className="mb-8">
                            {plan.is_custom_price ? (
                              <div className="text-4xl font-bold text-foreground">Custom</div>
                            ) : (
                              <>
                                <div className="flex items-baseline gap-2">
                                  <span className="text-5xl font-bold text-foreground">
                                    {billingCycle === 'monthly'
                                      ? formatPrice(plan.monthly_price || 0, plan.currency)
                                      : formatPrice(plan.yearly_price || 0, plan.currency)
                                    }
                                  </span>
                                </div>
                                <p className="text-muted-foreground mt-1">
                                  per {billingCycle === 'monthly' ? 'month' : 'year'}
                                </p>
                                {billingCycle === 'yearly' && plan.yearly_discount_percentage && plan.yearly_discount_percentage > 0 && (
                                  <p className="text-sm text-green-600 dark:text-green-400 mt-2 flex items-center gap-1">
                                    <TrendingUp className="w-4 h-4" />
                                    Save {plan.yearly_discount_percentage}% annually
                                  </p>
                                )}
                              </>
                            )}
                          </div>

                          {/* CTA Button */}
                          <Button
                            disabled={isCurrentPlan}
                            onClick={() => !isCurrentPlan && handleUpgradeClick(plan)}
                            className={`w-full py-6 rounded-xl font-semibold text-base transition-all duration-300 mb-8 ${
                              isCurrentPlan
                                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                                : plan.is_featured
                                  ? 'bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg'
                                  : 'bg-foreground hover:bg-foreground/90 text-background'
                            }`}
                          >
                            {isCurrentPlan ? 'Current Plan' : plan.is_custom_price ? 'Contact Sales' : 'Get Started'}
                          </Button>

                          {/* Features */}
                          <div className="space-y-4 flex-1">
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                              What's included
                            </p>
                            
                            {plan.monthly_credits !== null && (
                              <div className="flex items-center gap-3">
                                <div className={`p-1 rounded-full ${plan.is_featured ? 'bg-primary/10' : 'bg-muted'}`}>
                                  <Check className={`w-4 h-4 ${plan.is_featured ? 'text-primary' : 'text-green-600 dark:text-green-400'}`} />
                                </div>
                                <span className="text-muted-foreground">
                                  <strong className="text-foreground">
                                    {plan.monthly_credits === -1 ? 'Unlimited' : plan.monthly_credits.toLocaleString()}
                                  </strong> credits/month
                                </span>
                              </div>
                            )}

                            {plan.available_project !== null && (
                              <div className="flex items-center gap-3">
                                <div className={`p-1 rounded-full ${plan.is_featured ? 'bg-primary/10' : 'bg-muted'}`}>
                                  <Check className={`w-4 h-4 ${plan.is_featured ? 'text-primary' : 'text-green-600 dark:text-green-400'}`} />
                                </div>
                                <span className="text-muted-foreground">
                                  <strong className="text-foreground">
                                    {plan.available_project === -1 ? 'Unlimited' : plan.available_project}
                                  </strong> projects
                                </span>
                              </div>
                            )}

                            {plan.additional_credit_price !== null && (
                              <div className="flex items-center gap-3">
                                <div className={`p-1 rounded-full ${plan.is_featured ? 'bg-primary/10' : 'bg-muted'}`}>
                                  <Check className={`w-4 h-4 ${plan.is_featured ? 'text-primary' : 'text-green-600 dark:text-green-400'}`} />
                                </div>
                                <span className="text-muted-foreground">
                                  Extra credits at{" "}
                                  <strong className="text-foreground">
                                    {formatPrice(plan.additional_credit_price, plan.currency)}
                                  </strong>/100
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            )}
          </motion.div>
        )}

        {/* Credit Tab Content */}
        {billingTab === "credit" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="flex justify-center"
          >
            <div className="w-full max-w-xl">
              {/* Current Plan Card */}
              <div className="relative rounded-2xl overflow-hidden mb-8">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-primary/5" />
                <div className="relative p-6 border border-primary/20 rounded-2xl backdrop-blur-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-primary/10">
                        <CreditCard className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">Purchase Credits</h3>
                        <p className="text-sm text-muted-foreground">
                          Rate: <span className="text-primary font-medium">
                            {currentPlan?.additional_credit_price ? formatPrice(currentPlan.additional_credit_price, currentPlan.currency) : '—'}
                          </span> per 100 credits
                        </p>
                      </div>
                    </div>
                    {currentPlan && (
                      <span className="px-4 py-2 rounded-full bg-muted text-sm font-medium text-foreground">
                        {currentPlan.name}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Credit Amount Selection */}
              <div className="rounded-2xl bg-card border border-border p-8 space-y-8">
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-4 block">
                    Select credit amount
                  </label>

                  <div className="flex items-center gap-4 mb-6">
                    <input
                      type="number"
                      min="10"
                      step="10"
                      value={creditAmount}
                      onChange={(e) => {
                        const val = parseInt(e.target.value) || 10
                        setCreditAmount(Math.max(10, val))
                      }}
                      className="flex-1 h-14 rounded-xl border border-border bg-background px-4 text-xl font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                    />
                    <span className="text-muted-foreground font-medium">credits</span>
                  </div>

                  <input
                    type="range"
                    min="10"
                    max="1000"
                    step="10"
                    value={creditAmount}
                    onChange={(e) => setCreditAmount(parseInt(e.target.value))}
                    className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-primary"
                  />

                  <div className="flex gap-2 mt-6">
                    {[100, 250, 500, 1000].map((amount) => (
                      <button
                        key={amount}
                        onClick={() => setCreditAmount(amount)}
                        className={`flex-1 py-3 text-sm font-medium rounded-xl transition-all duration-300 ${
                          creditAmount === amount
                            ? "bg-primary text-primary-foreground shadow-lg"
                            : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        }`}
                      >
                        {amount}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Price Summary */}
                <div className="rounded-xl bg-muted/50 p-6 space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Credits</span>
                    <span className="text-foreground font-medium">{creditAmount} credits</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Price per credit</span>
                    <span className="text-foreground font-medium">
                      {currentPlan?.currency === 'VND'
                        ? `${(getPricePerCredit()).toLocaleString('vi-VN')} ₫`
                        : `$${getPricePerCredit().toFixed(3)}`
                      }
                    </span>
                  </div>
                  <div className="h-px bg-border" />
                  <div className="flex items-center justify-between">
                    <span className="text-foreground font-semibold">Total</span>
                    <span className="text-3xl font-bold text-foreground">
                      {currentPlan?.currency === 'VND'
                        ? `${parseFloat(totalPrice).toLocaleString('vi-VN')} ₫`
                        : `$${totalPrice}`
                      }
                    </span>
                  </div>
                </div>

                <Button
                  className="w-full py-6 rounded-xl font-semibold text-base bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg transition-all duration-300"
                  onClick={handleCreditPurchaseClick}
                >
                  <Zap className="w-5 h-5 mr-2" />
                  Purchase Credits
                </Button>

                <p className="text-xs text-muted-foreground text-center">
                  Credits will be added to your account immediately. No expiration.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* History Tab Content */}
        {billingTab === "history" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            {historyLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 rounded-xl bg-muted/50 animate-pulse" />
                ))}
              </div>
            ) : paymentHistory && paymentHistory.data.length > 0 ? (
              <div className="space-y-4">
                <div className="text-sm text-muted-foreground mb-6">
                  Showing {paymentHistory.offset + 1} - {Math.min(paymentHistory.offset + paymentHistory.limit, paymentHistory.total)} of {paymentHistory.total} transactions
                </div>

                {paymentHistory.data.map((order, index) => {
                  const getStatusDisplay = () => {
                    switch (order.status) {
                      case 'PAID':
                        return { icon: CheckCircle, text: 'Completed', color: 'text-green-600 dark:text-green-400', bg: 'bg-green-500/10' }
                      case 'PENDING':
                        return { icon: Clock, text: 'Pending', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-500/10' }
                      default:
                        return { icon: XCircle, text: 'Expired', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-500/10' }
                    }
                  }

                  const statusDisplay = getStatusDisplay()
                  const StatusIcon = statusDisplay.icon

                  return (
                    <motion.div
                      key={order.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      onClick={() => handleHistoryClick(order.id)}
                      className="group rounded-xl bg-card border border-border p-6 cursor-pointer hover:border-primary/50 hover:shadow-md transition-all duration-300"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`p-3 rounded-xl ${statusDisplay.bg}`}>
                            <Receipt className={`w-5 h-5 ${statusDisplay.color}`} />
                          </div>
                          <div>
                            <h4 className="font-semibold text-foreground mb-1">
                              {order.plan_code && order.billing_cycle
                                ? `${order.plan_code} Plan - ${order.billing_cycle === 'monthly' ? 'Monthly' : 'Yearly'}`
                                : 'Purchase'
                              }
                            </h4>
                            <p className="text-sm text-muted-foreground">
                              {new Date(order.created_at).toLocaleDateString('vi-VN', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <p className="text-lg font-bold text-foreground">
                              {order.amount.toLocaleString('vi-VN')} ₫
                            </p>
                          </div>
                          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${statusDisplay.bg}`}>
                            <StatusIcon className={`w-4 h-4 ${statusDisplay.color}`} />
                            <span className={`text-sm font-medium ${statusDisplay.color}`}>
                              {statusDisplay.text}
                            </span>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-8">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="p-3 rounded-xl bg-card border border-border hover:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      <ChevronLeft className="w-5 h-5 text-muted-foreground" />
                    </button>

                    <div className="flex items-center gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                        const showPage = page === 1 || page === totalPages || Math.abs(page - currentPage) <= 1

                        if (!showPage) {
                          if (page === currentPage - 2 || page === currentPage + 2) {
                            return <span key={page} className="px-2 text-muted-foreground">...</span>
                          }
                          return null
                        }

                        return (
                          <button
                            key={page}
                            onClick={() => setCurrentPage(page)}
                            className={`min-w-[44px] h-11 px-4 rounded-xl font-medium transition-all duration-300 ${
                              currentPage === page
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-card border border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
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
                      className="p-3 rounded-xl bg-card border border-border hover:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      <ChevronRight className="w-5 h-5 text-muted-foreground" />
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-20">
                <div className="p-4 rounded-xl bg-muted/50 inline-block mb-4">
                  <Receipt className="w-12 h-12 text-muted-foreground" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">No transactions yet</h3>
                <p className="text-muted-foreground">Your payment history will appear here</p>
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* Dialogs */}
      <InvoiceConfirmDialog
        open={invoiceDialogOpen}
        onOpenChange={setInvoiceDialogOpen}
        plan={selectedPlan}
        billingCycle={isPurchasingCredit ? 'monthly' : billingCycle}
        onConfirm={handlePaymentConfirm}
        isProcessing={isProcessingPayment}
        isPurchasingCredit={isPurchasingCredit}
      />

      <InvoiceDetailDialog
        open={invoiceDetailOpen}
        onOpenChange={setInvoiceDetailOpen}
        orderId={selectedOrderId}
      />

      <SePayQRDialog
        open={sepayDialogOpen}
        onOpenChange={setSepayDialogOpen}
        qrData={sepayQRData}
        onSuccess={handleSepaySuccess}
        onCancel={handleSepayCancel}
      />
    </div>
  )
}
