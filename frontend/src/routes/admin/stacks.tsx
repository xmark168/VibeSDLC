import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  Search,
  Plus,
  MoreVertical,
  Layers,
  Code2,
  Edit,
  Trash2,
  RefreshCw,
  Image as ImageIcon,
  FileCode,
  Package,
} from "lucide-react"
import { useStacks, useDeleteStack } from "@/queries/stacks"
import { requireRole } from "@/utils/auth"
import type { TechStack } from "@/types/stack"

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
import { Checkbox } from "@/components/ui/checkbox"
import { AdminLayout } from "@/components/admin/AdminLayout"
import { StackDialog } from "@/components/admin/stacks/StackDialog"
import { SkillEditorDialog } from "@/components/admin/stacks/SkillEditorDialog"
import { BoilerplateEditorDialog } from "@/components/admin/stacks/BoilerplateEditorDialog"

export const Route = createFileRoute("/admin/stacks")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: StacksAdminPage,
})

function StacksAdminPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [stackToDelete, setStackToDelete] = useState<TechStack | null>(null)
  const [deleteFiles, setDeleteFiles] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [skillDialogOpen, setSkillDialogOpen] = useState(false)
  const [boilerplateDialogOpen, setBoilerplateDialogOpen] = useState(false)
  const [stackToEdit, setStackToEdit] = useState<TechStack | null>(null)

  const queryParams = {
    search: searchTerm || undefined,
    is_active: statusFilter === "active" ? true : statusFilter === "inactive" ? false : undefined,
    limit: 100,
  }

  const { data: stacksData, isLoading, refetch } = useStacks(queryParams)
  const deleteStack = useDeleteStack()

  const handleDelete = async () => {
    if (!stackToDelete) return
    await deleteStack.mutateAsync({ stackId: stackToDelete.id, deleteFiles })
    setDeleteDialogOpen(false)
    setStackToDelete(null)
    setDeleteFiles(false)
    refetch()
  }

  const handleEditDetail = (stack: TechStack) => {
    setStackToEdit(stack)
    setEditDialogOpen(true)
  }

  const handleEditSkills = (stack: TechStack) => {
    setStackToEdit(stack)
    setSkillDialogOpen(true)
  }

  const handleEditBoilerplate = (stack: TechStack) => {
    setStackToEdit(stack)
    setBoilerplateDialogOpen(true)
  }

  const stats = stacksData
    ? {
        total: stacksData.count,
        active: stacksData.data.filter((s) => s.is_active).length,
      }
    : { total: 0, active: 0 }

  return (
    <AdminLayout>
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Stack Management</h1>
            <p className="text-muted-foreground">
              Manage technology stacks and their skill configurations
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)} size="sm">
              <Plus className="w-4 h-4 mr-2" />
              New Stack
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Total Stacks</div>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="text-sm font-medium">Active Stacks</div>
              <Code2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active}</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap items-center gap-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or code..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>

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
            </div>
          </CardContent>
        </Card>

        {/* Stacks Table */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-8 space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stacksData?.data.length === 0 ? (
              <div className="text-center py-20">
                <Layers className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No stacks found</h3>
                <p className="text-muted-foreground mb-6">Create your first stack to get started.</p>
                <Button onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Stack
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Image</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Stack Config</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stacksData?.data.map((stack) => (
                    <TableRow
                      key={stack.id}
                      className="cursor-pointer"
                      onClick={() => handleEditDetail(stack)}
                    >
                      <TableCell>
                        {stack.image ? (
                          <img
                            src={stack.image}
                            alt={stack.name}
                            className="w-10 h-10 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                            <ImageIcon className="w-5 h-5 text-muted-foreground" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-primary">{stack.code}</TableCell>
                      <TableCell className="font-medium">{stack.name}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(stack.stack_config || {})
                            .filter(([_, value]) => !Array.isArray(value) && typeof value !== 'object' && value !== null)
                            .slice(0, 3)
                            .map(([key, value]) => (
                              <Badge key={key} variant="secondary" className="text-xs">
                                {key}: {String(value)}
                              </Badge>
                            ))}
                          {Array.isArray((stack.stack_config as Record<string, unknown>)?.services) && (
                            <Badge variant="outline" className="text-xs">
                              {((stack.stack_config as Record<string, unknown>).services as unknown[]).length} service{((stack.stack_config as Record<string, unknown>).services as unknown[]).length > 1 ? 's' : ''}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-2 h-2 rounded-full ${
                              stack.is_active ? "bg-green-500" : "bg-muted-foreground"
                            }`}
                          />
                          <Badge variant={stack.is_active ? "default" : "secondary"}>
                            {stack.is_active ? "Active" : "Inactive"}
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
                            <DropdownMenuItem onClick={() => handleEditDetail(stack)}>
                              <Edit className="w-4 h-4 mr-2" />
                              Edit Detail
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleEditSkills(stack)}>
                              <FileCode className="w-4 h-4 mr-2" />
                              Edit Skills
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleEditBoilerplate(stack)}>
                              <Package className="w-4 h-4 mr-2" />
                              Edit Boilerplate
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => {
                                setStackToDelete(stack)
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
      <StackDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          refetch()
          setCreateDialogOpen(false)
        }}
      />

      {/* Edit Detail Dialog */}
      {stackToEdit && (
        <StackDialog
          open={editDialogOpen}
          onOpenChange={(open) => {
            setEditDialogOpen(open)
            if (!open) setStackToEdit(null)
          }}
          stack={stackToEdit}
          onSuccess={() => {
            refetch()
            setEditDialogOpen(false)
            setStackToEdit(null)
          }}
        />
      )}

      {/* Edit Skills Dialog */}
      {stackToEdit && (
        <SkillEditorDialog
          open={skillDialogOpen}
          onOpenChange={(open) => {
            setSkillDialogOpen(open)
            if (!open) setStackToEdit(null)
          }}
          stack={stackToEdit}
        />
      )}

      {/* Edit Boilerplate Dialog */}
      {stackToEdit && (
        <BoilerplateEditorDialog
          open={boilerplateDialogOpen}
          onOpenChange={(open) => {
            setBoilerplateDialogOpen(open)
            if (!open) setStackToEdit(null)
          }}
          stack={stackToEdit}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Stack</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{stackToDelete?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex items-center gap-2 py-2">
            <Checkbox
              id="deleteFiles"
              checked={deleteFiles}
              onCheckedChange={(checked) => setDeleteFiles(checked as boolean)}
            />
            <label htmlFor="deleteFiles" className="text-sm text-muted-foreground">
              Also delete skill files from disk
            </label>
          </div>
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
