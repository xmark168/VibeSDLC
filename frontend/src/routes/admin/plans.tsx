import { createFileRoute } from "@tanstack/react-router"
import { requireRole } from "@/utils/auth"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Edit, Trash2, RefreshCw, Layers, Zap } from "lucide-react"

export const Route = createFileRoute("/admin/plans")({
  beforeLoad: async () => {
    await requireRole('admin')
  },
  component: RouteComponent,
})

type Plan = {
  id: string
  name: string
  price: number
  credits: number | "unlimited"
  projects: number | "unlimited"
  pricePerCredit: number
  features: string[]
  isActive: boolean
}

function RouteComponent() {
  const [plans] = useState<Plan[]>([
    {
      id: "1",
      name: "Free",
      price: 0,
      credits: 100,
      projects: 2,
      pricePerCredit: 10,
      features: ["100 credits / month", "2 projects", "$10 / 100 credits"],
      isActive: true,
    },
    {
      id: "2",
      name: "Pro",
      price: 20,
      credits: 500,
      projects: 10,
      pricePerCredit: 8,
      features: ["500 credits / month", "10 projects", "$8 / 100 credits"],
      isActive: true,
    },
    {
      id: "3",
      name: "Max",
      price: 100,
      credits: "unlimited",
      projects: "unlimited",
      pricePerCredit: 5,
      features: ["Unlimited credits / month", "Unlimited projects", "$5 / 100 credits"],
      isActive: true,
    },
  ])

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Plan Management</h1>
          <p className="text-muted-foreground">
            Create and manage subscription plans and pricing
          </p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Create New Plan
        </Button>
      </div>

      {/* Plans Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-2xl">{plan.name}</CardTitle>
                  <CardDescription>
                    {plan.isActive ? (
                      <span className="text-green-500">Active</span>
                    ) : (
                      <span className="text-muted-foreground">Inactive</span>
                    )}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Price */}
              <div>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">${plan.price}</span>
                  <span className="text-muted-foreground">/ month</span>
                </div>
              </div>

              {/* Features */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <RefreshCw className="h-4 w-4 text-muted-foreground" />
                  <span>
                    <strong>{plan.credits === "unlimited" ? "Unlimited" : plan.credits}</strong> credits / month
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Layers className="h-4 w-4 text-muted-foreground" />
                  <span>
                    <strong>{plan.projects === "unlimited" ? "Unlimited" : plan.projects}</strong> projects
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-muted-foreground" />
                  <span>
                    <strong>${plan.pricePerCredit}</strong> / 100 credits
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="pt-4 border-t space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Active Users:</span>
                  <span className="font-medium">
                    {plan.name === "Free" ? "1,234" : plan.name === "Pro" ? "456" : "78"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Monthly Revenue:</span>
                  <span className="font-medium">
                    {plan.name === "Free" ? "$0" : plan.name === "Pro" ? "$9,120" : "$7,800"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Active Plans
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">3</div>
            <p className="text-xs text-muted-foreground mt-1">
              All plans are currently active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Subscribers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">1,768</div>
            <p className="text-xs text-muted-foreground mt-1">
              +12% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Monthly Recurring Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">$16,920</div>
            <p className="text-xs text-muted-foreground mt-1">
              +8% from last month
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
