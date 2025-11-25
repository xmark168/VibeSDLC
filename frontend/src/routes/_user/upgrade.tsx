import { createFileRoute } from '@tanstack/react-router'
import { useState } from "react"
import { Info, RefreshCw, Layers, Zap, Receipt, XCircle, CheckCircle, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeaderProject } from "@/components/projects/header"

export const Route = createFileRoute('/_user/upgrade')({
  component: RouteComponent,
})

type BillingTab = "plan" | "credit" | "history"

function RouteComponent() {
  const [billingTab, setBillingTab] = useState<BillingTab>("plan")
  const [creditAmount, setCreditAmount] = useState<number>(100)

  // Mock payment history data
  const paymentHistory = [
    {
      id: "dc066a80-368b-40de-bf70-f8a0bbaac417",
      title: "Tên gói hoặc số credits đã mua",
      amount: "Số tiền đã thanh toán",
      status: "expired" as const,
      createdAt: "2025-11-24 23:06:03",
      paidAt: "2025-11-24 23:06:03",
    },
    {
      id: "bc166b90-468b-50de-cf80-g9b1ccbd528",
      title: "Pro Plan - Monthly",
      amount: "$20.00",
      status: "completed" as const,
      createdAt: "2025-11-20 14:32:10",
      paidAt: "2025-11-20 14:32:15",
    },
    {
      id: "ad255c01-579c-61ef-dg91-h0c2ddce639",
      title: "500 Credits Purchase",
      amount: "$40.00",
      status: "pending" as const,
      createdAt: "2025-11-18 09:15:22",
      paidAt: null,
    },
  ]

  // Pricing based on current plan (Free plan for now)
  const currentPlan = "free" // TODO: Get from user state
  const getPricePerCredit = () => {
    switch (currentPlan) {
      case "free":
        return 0.1 // $10 / 100 credits = $0.1 per credit
      case "pro":
        return 0.08 // $8 / 100 credits = $0.08 per credit
      case "max":
        return 0.05 // $5 / 100 credits = $0.05 per credit
      default:
        return 0.1
    }
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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Free Plan */}
              <div className="bg-secondary/20 rounded-lg p-6 border flex flex-col">
                <h4 className="text-xl font-semibold mb-2">Free</h4>
                <div className="mb-6">
                  <span className="text-4xl font-bold">$0</span>
                  <span className="text-muted-foreground"> / month</span>
                </div>
                <Button
                  disabled
                  className="w-full bg-secondary text-foreground hover:bg-secondary cursor-not-allowed mb-6"
                >
                  Your current plan
                </Button>

                {/* Features */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    <span><strong>100</strong> credits / month</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Layers className="h-4 w-4 text-muted-foreground" />
                    <span><strong>2</strong> project</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Zap className="h-4 w-4 text-muted-foreground" />
                    <span><span className="font-semibold">$10</span> / 100 credits</span>
                  </div>
                </div>
              </div>

              {/* Pro Plan */}
              <div className="bg-secondary/20 rounded-lg p-6 border flex flex-col">
                <h4 className="text-xl font-semibold mb-2">Pro</h4>
                <div className="mb-6">
                  <span className="text-4xl font-bold">$20</span>
                  <span className="text-muted-foreground"> / month</span>
                </div>
                <Button className="w-full bg-primary hover:bg-primary/90 mb-6">
                  Upgrade
                </Button>

                {/* Features */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    <span><strong>500</strong> credits / month</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Layers className="h-4 w-4 text-muted-foreground" />
                    <span><strong>10</strong> project</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Zap className="h-4 w-4 text-muted-foreground" />
                    <span><span className="font-semibold">$8</span> / 100 credits</span>
                  </div>
                </div>
              </div>

              {/* Max Plan */}
              <div className="bg-secondary/20 rounded-lg p-6 border flex flex-col">
                <h4 className="text-xl font-semibold mb-2">Max</h4>
                <div className="mb-6">
                  <span className="text-4xl font-bold">$100</span>
                  <span className="text-muted-foreground"> / month</span>
                </div>
                <Button className="w-full bg-primary hover:bg-primary/90 mb-6">
                  Upgrade
                </Button>

                {/* Features */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    <span><strong>Unlimited</strong> credits / month</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Layers className="h-4 w-4 text-muted-foreground" />
                    <span><strong>Unlimited</strong> project</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Zap className="h-4 w-4 text-muted-foreground" />
                    <span><span className="font-semibold">$5</span> / 100 credits</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {billingTab === "credit" && (
          <div className="py-6 flex justify-center">
            <div className="max-w-xl w-full">
              {/* Plan Info Card */}
              <div className="bg-secondary/30 rounded-lg p-6 mb-8">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold">Purchase Credits</h3>
                  <span className="text-sm px-3 py-1 bg-secondary rounded-md">
                    {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} Plan
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Your plan rate: <span className="font-semibold text-foreground">${(getPricePerCredit() * 100).toFixed(0)}</span> per 100 credits
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
                    <span className="font-medium">${getPricePerCredit().toFixed(3)}</span>
                  </div>
                  <div className="border-t pt-3 flex items-center justify-between">
                    <span className="font-semibold">Total</span>
                    <span className="text-2xl font-bold">${totalPrice}</span>
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
            {/* Payment History List */}
              <div className="space-y-4">
                {paymentHistory.map((payment) => (
                  <div
                    key={payment.id}
                    className="bg-secondary/20 rounded-lg p-6 space-y-4"
                  >
                    {/* Header with ID and Status */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Receipt className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-mono text-muted-foreground">
                          {payment.id}
                        </span>
                        <button
                          onClick={() => navigator.clipboard.writeText(payment.id)}
                          className="text-primary hover:text-primary/80 text-sm font-medium transition-colors"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="flex items-center gap-2">
                        {payment.status === "expired" && (
                          <>
                            <XCircle className="h-4 w-4 text-destructive" />
                            <span className="text-sm font-medium text-destructive">
                              Expired
                            </span>
                          </>
                        )}
                        {payment.status === "completed" && (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-sm font-medium text-green-500">
                              Completed
                            </span>
                          </>
                        )}
                        {payment.status === "pending" && (
                          <>
                            <Clock className="h-4 w-4 text-yellow-500" />
                            <span className="text-sm font-medium text-yellow-500">
                              Pending
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Payment Details and Timestamps */}
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <h4 className="font-semibold">{payment.title}</h4>
                        <p className="text-sm text-muted-foreground">{payment.amount}</p>
                      </div>
                      <div className="space-y-1 text-right">
                        <p className="text-sm text-muted-foreground">
                          Created at: {payment.createdAt}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Paid at: {payment.paidAt || "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}

                {paymentHistory.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    No payment history found
                  </div>
                )}
              </div>
          </div>
        )}
      </div>
    </div>
  )
}
