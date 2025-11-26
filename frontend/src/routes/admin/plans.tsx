import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  Search,
  Plus,
  MoreVertical,
  TrendingUp,
  DollarSign,
  Users,
  Package,
  Filter,
  Star,
  Edit,
  Trash2,
} from "lucide-react"
import { usePlans, useDeletePlan } from "@/queries/plans"
import { requireRole } from "@/utils/auth"
import type { Plan } from "@/types/plan"
import {
  formatPrice,
  getTierLabel,
  getTierVariant,
  formatDiscount,
} from "@/apis/plans"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
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

  // Build query params
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

  // Calculate stats
  const stats = plansData
    ? {
        total: plansData.count,
        active: plansData.data.filter((p) => p.is_active).length,
        featured: plansData.data.filter((p) => p.is_featured).length,
        totalRevenue: plansData.data
          .filter((p) => p.is_active)
          .reduce((sum, p) => sum + (p.price || 0), 0),
      }
    : { total: 0, active: 0, featured: 0, totalRevenue: 0 }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden">
      {/* Texture overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDQwIDAgTCAwIDAgMCA0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDIpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-40" />

      <div className="relative z-10 container mx-auto px-6 py-12">
        {/* Header Section */}
        <header className="mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold">Plan Management</h1>
              <p className="text-muted-foreground">
                Manage pricing tiers, billing cycles, and plan features for your platform.
              </p>
            </div>
            <Button
              onClick={() => setCreateDialogOpen(true)}
              size="lg"
              className="bg-amber-600 hover:bg-amber-700 text-white shadow-lg shadow-amber-900/50 transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-amber-900/70"
            >
              <Plus className="w-5 h-5 mr-2" />
              New Plan
            </Button>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <StatCard
              icon={<Package className="w-6 h-6" />}
              label="Total Plans"
              value={stats.total}
              delay="100"
            />
            <StatCard
              icon={<Users className="w-6 h-6" />}
              label="Active Plans"
              value={stats.active}
              delay="200"
            />
            <StatCard
              icon={<Star className="w-6 h-6" />}
              label="Featured"
              value={stats.featured}
              delay="300"
            />
            <StatCard
              icon={<DollarSign className="w-6 h-6" />}
              label="Total Value"
              value={formatPrice(stats.totalRevenue)}
              delay="400"
            />
          </div>

          {/* Filters Bar */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-700 delay-500">
            <div className="flex justify-start gap-2">
              <div className="relative md:col-span-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <Input
                  placeholder="Search plans by name, code, or description..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-11 bg-slate-950/50 border-slate-700/50 text-white placeholder:text-slate-500 focus:border-amber-500/50 transition-colors w-100"
                />
              </div>

              <Select value={tierFilter} onValueChange={setTierFilter}>
                <SelectTrigger className="bg-slate-950/50 border-slate-700/50 text-white">
                  <SelectValue placeholder="Tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="pay">Pay</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="bg-slate-950/50 border-slate-700/50 text-white">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-4 mt-4 pt-4 border-t border-slate-800/50">
              <Filter className="w-4 h-4 text-slate-500" />
              <span className="text-sm text-slate-400">Sort by:</span>
              <Select value={orderBy} onValueChange={(v: any) => setOrderBy(v)}>
                <SelectTrigger className="w-40 bg-slate-950/50 border-slate-700/50 text-white h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sort_index">Order</SelectItem>
                  <SelectItem value="price">Price</SelectItem>
                  <SelectItem value="created_at">Created Date</SelectItem>
                  <SelectItem value="name">Name</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </header>

        {/* Plans Table */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl shadow-2xl overflow-hidden">
          {isLoading ? (
            <div className="p-8 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-slate-800/30 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : plansData?.data.length === 0 ? (
            <div className="text-center py-20">
              <Package className="w-16 h-16 text-slate-700 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-slate-400 mb-2">No plans found</h3>
              <p className="text-slate-500 mb-6">Create your first plan to get started.</p>
              <Button onClick={() => setCreateDialogOpen(true)} className="bg-amber-600 hover:bg-amber-700">
                <Plus className="w-4 h-4 mr-2" />
                Create Plan
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-slate-800/30">
                  <TableHead className="text-slate-400 font-semibold">Code</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Name</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Order</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Monthly Price</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Yearly Price</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Monthly Credits</TableHead>
                  <TableHead className="text-slate-400 font-semibold">100 Credits Price</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Projects</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Featured</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Status</TableHead>
                  <TableHead className="text-slate-400 font-semibold text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plansData?.data.map((plan) => (
                  <TableRow
                    key={plan.id}
                    className="border-slate-800 hover:bg-slate-800/30 transition-colors"
                  >
                    {/* Code */}
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Badge variant={getTierVariant(plan.tier)} className="text-xs">
                          {plan.code}
                        </Badge>
                      </div>
                    </TableCell>

                    {/* Name */}
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-white font-semibold">{plan.name}</span>
                      </div>
                    </TableCell>

                    {/* Sort Index */}
                    <TableCell>
                      <span className="text-slate-300 font-mono">{plan.sort_index}</span>
                    </TableCell>

                    {/* Monthly Price */}
                    <TableCell>
                      {plan.is_custom_price ? (
                        <span className="text-slate-500">—</span>
                      ) : plan.monthly_price !== null && plan.monthly_price !== undefined ? (
                        <span className="text-white font-semibold">
                          {formatPrice(plan.monthly_price, plan.currency)}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </TableCell>

                    {/* Yearly Price */}
                    <TableCell>
                      {plan.is_custom_price ? (
                        <span className="text-slate-500">—</span>
                      ) : plan.yearly_price !== null && plan.yearly_price !== undefined ? (
                        <div className="flex flex-col">
                          <span className="text-white font-semibold">
                            {formatPrice(plan.yearly_price, plan.currency)}
                          </span>
                          {plan.yearly_discount_percentage && plan.yearly_discount_percentage > 0 && (
                            <span className="text-xs text-emerald-400">
                              {formatDiscount(plan.yearly_discount_percentage)}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </TableCell>

                    {/* Monthly Credits */}
                    <TableCell>
                      <span className="text-slate-300">
                        {plan.monthly_credits !== null ? plan.monthly_credits.toLocaleString() : '-'}
                      </span>
                    </TableCell>

                    {/* 100 Credits Price */}
                    <TableCell>
                      <span className="text-amber-400 font-semibold">
                        {plan.additional_credit_price !== null
                          ? formatPrice(plan.additional_credit_price, plan.currency)
                          : '-'}
                      </span>
                    </TableCell>

                    {/* Projects */}
                    <TableCell>
                      <span className="text-slate-300">
                        {plan.available_project !== null ? plan.available_project : '-'}
                      </span>
                    </TableCell>

                    {/* Featured */}
                    <TableCell>
                      {plan.is_featured ? (
                        <div className="flex items-center gap-1.5">
                          <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                          <span className="text-sm text-amber-400 font-medium">Featured</span>
                        </div>
                      ) : (
                        <span className="text-slate-500 text-sm">—</span>
                      )}
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${plan.is_active ? 'bg-emerald-400' : 'bg-slate-600'} animate-pulse`}
                        />
                        <span className={`text-sm font-medium ${plan.is_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                          {plan.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </TableCell>

                    {/* Actions */}
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-slate-400 hover:text-white hover:bg-slate-800/50"
                          >
                            <MoreVertical className="w-5 h-5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-slate-900 border-slate-800">
                          <DropdownMenuItem onClick={() => handleEdit(plan)} className="text-white hover:bg-slate-800">
                            <Edit className="w-4 h-4 mr-2" />
                            Edit Plan
                          </DropdownMenuItem>
                          <DropdownMenuSeparator className="bg-slate-800" />
                          <DropdownMenuItem
                            onClick={() => {
                              setPlanToDelete(plan)
                              setDeleteDialogOpen(true)
                            }}
                            className="text-red-400 hover:bg-red-950/50 hover:text-red-300"
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
        </div>
      </div>

      {/* Dialogs */}
      <PlanDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          refetch()
          setCreateDialogOpen(false)
        }}
        initialData={planToEdit as any}
      />

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

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-slate-900 border-slate-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Delete Plan</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">
              Are you sure you want to delete "{planToDelete?.name}"? This action cannot be undone.
              {planToDelete?.is_active && (
                <span className="block mt-2 text-amber-500 font-medium">
                  Warning: This plan is currently active.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-slate-800 text-white border-slate-700 hover:bg-slate-700">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// Stat Card Component
function StatCard({
  icon,
  label,
  value,
  delay,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  delay: string
}) {
  return (
    <div
      className="group bg-gradient-to-br from-slate-900/80 to-slate-900/40 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 shadow-xl hover:shadow-2xl hover:shadow-amber-900/10 transition-all duration-500 hover:scale-105 hover:border-amber-500/30 animate-in fade-in slide-in-from-bottom-4"
      style={{ animationDelay: `${delay}ms`, animationDuration: "700ms" }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-amber-500/10 rounded-xl group-hover:bg-amber-500/20 transition-colors duration-300">
          <div className="text-amber-400">{icon}</div>
        </div>
      </div>
      <div className="space-y-1">
        <p className="text-3xl font-bold text-white font-serif">
          {value}
        </p>
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  )
}
