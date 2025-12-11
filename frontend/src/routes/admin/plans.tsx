import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  Search,
  Plus,
  MoreVertical,
  DollarSign,
  Users,
  Package,
  Star,
  Edit,
  Trash2,
  RefreshCw,
} from "lucide-react"
import { usePlans, useDeletePlan } from "@/queries/plans"
import { requireRole } from "@/utils/auth"
import type { Plan } from "@/types/plan"
import {
  formatPrice,
  getTierVariant,
  formatDiscount,
} from "@/apis/plans"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { PlanDialog } from "@/components/admin/PlanDialog"
import { AdminLayout } from "@/components/admin/AdminLayout"

export const Route = createFileRoute("/admin/plans")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: PlansAdminPage,
})

function PlansAdminPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [tierFilter, setTierFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [orderBy, setOrderBy] = useState<"sort_index" | "price" | "created_at" | "name">("sort_index")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [planToDelete, setPlanToDelete] = useState<Plan | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [planToEdit, setPlanToEdit] = useState<Plan | null>(null)

  const queryParams = {
    search: searchTerm || undefined,
    tier: tierFilter !== "all" ? tierFilter : undefined,
    is_active: statusFilter === "active" ? true : statusFilter === "inactive" ? false : undefined,
    order_by: orderBy,
    limit: 100,
  }

  const { data: plansData, isLoading, refetch } = usePlans(queryParams)
  const deletePlan = useDeletePlan()

  const handleDelete = async () => {
    if (!planToDelete) return
    await deletePlan.mutateAsync(planToDelete.id)
    setDeleteDialogOpen(false)
    setPlanToDelete(null)
    refetch()
  }

  const handleEdit = (plan: Plan) => {
    setPlanToEdit(plan)
    setEditDialogOpen(true)
  }

  const stats = plansData
    ? {
        total: plansData.count,
        active: plansData.data.filter((p) => p.is_active).length,
        featured: plansData.data.filter((p) => p.is_featured).length,
        totalRevenue: plansData.data
          .filter((p) => p.is_active && !p.is_custom_price)
          .reduce((sum, p) => sum + (p.monthly_price || 0), 0),
      }
    : { total: 0, active: 0, featured: 0, totalRevenue: 0 }

  return (
    <AdminLayout>
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Plan Management</h1>
            <p className="text-muted-foreground">
              Manage pricing tiers, billing cycles, and plan features
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)} size="sm">
              <Plus className="w-4 h-4 mr-2" />
              New Plan
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Total Plans</div>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Active Plans</div>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Featured</div>
              <Star className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.featured}</div>
            </CardContent>
          </Card>
          {/* <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Total Value</div>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatPrice(stats.totalRevenue)}</div>
            </CardContent>
          </Card> */}
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap items-center gap-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, code..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>

              <Select value={tierFilter} onValueChange={setTierFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="pay">Pay</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>

              <Select value={orderBy} onValueChange={(v: any) => setOrderBy(v)}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sort_index">Order</SelectItem>
                  <SelectItem value="price">Price</SelectItem>
                  <SelectItem value="created_at">Created</SelectItem>
                  <SelectItem value="name">Name</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Plans Table */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-8 space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
                ))}
              </div>
            ) : plansData?.data.length === 0 ? (
              <div className="text-center py-20">
                <Package className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No plans found</h3>
                <p className="text-muted-foreground mb-6">Create your first plan to get started.</p>
                <Button onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Plan
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Order</TableHead>
                    <TableHead>Monthly</TableHead>
                    <TableHead>Yearly</TableHead>
                    <TableHead>Credits</TableHead>
                    <TableHead>Projects</TableHead>
                    <TableHead>Featured</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plansData?.data.map((plan) => (
                    <TableRow
                      key={plan.id}
                      className="cursor-pointer"
                      onClick={() => handleEdit(plan)}
                    >
                      <TableCell>
                        <Badge variant={getTierVariant(plan.tier)} className="text-xs">
                          {plan.code}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{plan.name}</TableCell>
                      <TableCell className="font-mono text-muted-foreground">
                        {plan.sort_index}
                      </TableCell>
                      <TableCell>
                        {plan.is_custom_price ? (
                          <span className="text-muted-foreground">Custom</span>
                        ) : plan.monthly_price != null ? (
                          formatPrice(plan.monthly_price, plan.currency)
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {plan.is_custom_price ? (
                          <span className="text-muted-foreground">Custom</span>
                        ) : plan.yearly_price != null ? (
                          <div className="flex flex-col">
                            <span>{formatPrice(plan.yearly_price, plan.currency)}</span>
                            {plan.yearly_discount_percentage && plan.yearly_discount_percentage > 0 && (
                              <span className="text-xs text-green-500">
                                {formatDiscount(plan.yearly_discount_percentage)}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {plan.monthly_credits != null ? plan.monthly_credits.toLocaleString() : '—'}
                      </TableCell>
                      <TableCell>
                        {plan.available_project != null ? plan.available_project : '—'}
                      </TableCell>
                      <TableCell>
                        {plan.is_featured ? (
                          <div className="flex items-center gap-1">
                            <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-2 h-2 rounded-full ${
                              plan.is_active ? "bg-green-500" : "bg-muted-foreground"
                            }`}
                          />
                          <Badge variant={plan.is_active ? "default" : "secondary"}>
                            {plan.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEdit(plan)}>
                              <Edit className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => {
                                setPlanToDelete(plan)
                                setDeleteDialogOpen(true)
                              }}
                              className="text-destructive"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Dialog */}
      <PlanDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          refetch()
          setCreateDialogOpen(false)
        }}
      />

      {/* Edit Dialog */}
      <PlanDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        plan={planToEdit || undefined}
        onSuccess={() => {
          refetch()
          setEditDialogOpen(false)
          setPlanToEdit(null)
        }}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Plan</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{planToDelete?.name}"? This action cannot be undone.
              {planToDelete?.is_active && (
                <span className="block mt-2 text-amber-500 font-medium">
                  Warning: This plan is currently active.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  )
}
