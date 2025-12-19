import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  Search,
  Plus,
  MoreVertical,
  Users,
  UserCheck,
  UserX,
  Shield,
  Edit,
  Lock,
  Unlock,
  RefreshCw,
  Trash2,
} from "lucide-react"
import {
  useAdminUsers,
  useUserStats,
  useDeleteUser,
  useLockUser,
  useUnlockUser,
  useBulkLockUsers,
  useBulkUnlockUsers,
  useBulkDeleteUsers,
} from "@/queries/users"
import { requireRole } from "@/utils/auth"
import type { UserAdmin } from "@/types/user"
import { getRoleLabel, getRoleVariant, getStatusLabel, getStatusVariant } from "@/apis/users"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
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
import { UserDialog } from "@/components/admin/users"
import { formatDistanceToNow } from "date-fns"
import { AdminLayout } from "@/components/admin/AdminLayout"

export const Route = createFileRoute("/admin/users")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: UsersAdminPage,
})

function UsersAdminPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [roleFilter, setRoleFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [orderBy, setOrderBy] = useState<string>("created_at")

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [userToEdit, setUserToEdit] = useState<UserAdmin | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [userToDelete, setUserToDelete] = useState<UserAdmin | null>(null)

  // Bulk selection
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())
  const [bulkActionDialogOpen, setBulkActionDialogOpen] = useState(false)
  const [bulkAction, setBulkAction] = useState<"lock" | "unlock" | "delete" | null>(null)

  // Query params
  const queryParams = {
    search: searchTerm || undefined,
    role: roleFilter !== "all" ? roleFilter : undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
    order_by: orderBy,
    order_dir: "desc" as const,
    limit: 100,
  }

  const { data: usersData, isLoading, refetch } = useAdminUsers(queryParams)
  const { data: stats } = useUserStats()

  // Mutations
  const deleteUser = useDeleteUser()
  const lockUser = useLockUser()
  const unlockUser = useUnlockUser()
  const bulkLock = useBulkLockUsers()
  const bulkUnlock = useBulkUnlockUsers()
  const bulkDelete = useBulkDeleteUsers()

  const handleEdit = (user: UserAdmin) => {
    setUserToEdit(user)
    setEditDialogOpen(true)
  }

  const handleDelete = async () => {
    if (!userToDelete) return
    await deleteUser.mutateAsync(userToDelete.id)
    setDeleteDialogOpen(false)
    setUserToDelete(null)
    refetch()
  }

  const handleLock = async (user: UserAdmin) => {
    await lockUser.mutateAsync(user.id)
    refetch()
  }

  const handleUnlock = async (user: UserAdmin) => {
    await unlockUser.mutateAsync(user.id)
    refetch()
  }

  // Bulk actions
  const toggleSelectAll = () => {
    if (selectedUsers.size === usersData?.data.length) {
      setSelectedUsers(new Set())
    } else {
      setSelectedUsers(new Set(usersData?.data.map((u) => u.id) || []))
    }
  }

  const toggleSelectUser = (userId: string) => {
    const newSelected = new Set(selectedUsers)
    if (newSelected.has(userId)) {
      newSelected.delete(userId)
    } else {
      newSelected.add(userId)
    }
    setSelectedUsers(newSelected)
  }

  const handleBulkAction = async () => {
    const userIds = Array.from(selectedUsers)
    if (bulkAction === "lock") {
      await bulkLock.mutateAsync(userIds)
    } else if (bulkAction === "unlock") {
      await bulkUnlock.mutateAsync(userIds)
    } else if (bulkAction === "delete") {
      await bulkDelete.mutateAsync(userIds)
    }
    setSelectedUsers(new Set())
    setBulkActionDialogOpen(false)
    setBulkAction(null)
    refetch()
  }

  const openBulkActionDialog = (action: "lock" | "unlock" | "delete") => {
    setBulkAction(action)
    setBulkActionDialogOpen(true)
  }

  return (
    <AdminLayout>
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground">
            Manage user accounts, roles, and permissions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)} size="sm">
            <Plus className="w-4 h-4 mr-2" />
            New User
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="text-sm font-medium">Total Users</div>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="text-sm font-medium">Active Users</div>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_users || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="text-sm font-medium">Admins</div>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.admin_users || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="text-sm font-medium">Locked</div>
            <UserX className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.locked_users || 0}</div>
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
                placeholder="Search by name, email, or username..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>

            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="user">User</SelectItem>
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
                <SelectItem value="locked">Locked</SelectItem>
              </SelectContent>
            </Select>

            <Select value={orderBy} onValueChange={setOrderBy}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_at">Created Date</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="full_name">Name</SelectItem>
              </SelectContent>
            </Select>

            {/* Bulk Actions */}
            {selectedUsers.size > 0 && (
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-sm text-muted-foreground">
                  {selectedUsers.size} selected
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openBulkActionDialog("lock")}
                >
                  <Lock className="w-4 h-4 mr-1" />
                  Lock
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openBulkActionDialog("unlock")}
                >
                  <Unlock className="w-4 h-4 mr-1" />
                  Unlock
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => openBulkActionDialog("delete")}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Delete
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
              ))}
            </div>
          ) : usersData?.data.length === 0 ? (
            <div className="text-center py-20">
              <Users className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">No users found</h3>
              <p className="text-muted-foreground mb-6">Create your first user to get started.</p>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create User
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedUsers.size === usersData?.data.length && usersData?.data.length > 0}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {usersData?.data.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedUsers.has(user.id)}
                        onCheckedChange={() => toggleSelectUser(user.id)}
                      />
                    </TableCell>

                    {/* User Info */}
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary font-medium">
                          {(user.full_name || user.email).charAt(0).toUpperCase()}
                        </div>
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {user.full_name || user.username || "—"}
                          </span>
                          {user.username && user.full_name && (
                            <span className="text-xs text-muted-foreground">@{user.username}</span>
                          )}
                        </div>
                      </div>
                    </TableCell>

                    {/* Email */}
                    <TableCell>{user.email}</TableCell>

                    {/* Role */}
                    <TableCell>
                      <Badge variant={getRoleVariant(user.role)}>
                        {getRoleLabel(user.role)}
                      </Badge>
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${
                            user.is_locked
                              ? "bg-destructive"
                              : user.is_active
                              ? "bg-green-500"
                              : "bg-muted-foreground"
                          }`}
                        />
                        <Badge variant={getStatusVariant(user)}>
                          {getStatusLabel(user)}
                        </Badge>
                      </div>
                    </TableCell>

                    {/* Provider */}
                    <TableCell>
                      <span className="text-muted-foreground text-sm">
                        {user.login_provider || "Email"}
                      </span>
                    </TableCell>

                    {/* Created */}
                    <TableCell>
                      <span className="text-muted-foreground text-sm">
                        {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
                      </span>
                    </TableCell>

                    {/* Actions */}
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(user)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit User
                          </DropdownMenuItem>

                          <DropdownMenuSeparator />

                          {user.is_locked ? (
                            <DropdownMenuItem onClick={() => handleUnlock(user)}>
                              <Unlock className="w-4 h-4 mr-2" />
                              Unlock
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => handleLock(user)}>
                              <Lock className="w-4 h-4 mr-2" />
                              Lock
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuSeparator />

                          <DropdownMenuItem
                            onClick={() => {
                              setUserToDelete(user)
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

      {/* Dialogs */}
      <UserDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          refetch()
          setCreateDialogOpen(false)
        }}
      />

      <UserDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        user={userToEdit || undefined}
        onSuccess={() => {
          refetch()
          setEditDialogOpen(false)
          setUserToEdit(null)
        }}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold">{userToDelete?.email}</span>? 
              <br />
              <br />
              <span className="text-destructive font-medium">⚠️ Warning:</span> This action cannot be undone. All user data including:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>All projects owned by this user</li>
                <li>All stories, epics, and agents</li>
                <li>Subscription and billing information</li>
                <li>Linked OAuth accounts</li>
              </ul>
              will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete} 
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Bulk Action Confirmation */}
      <AlertDialog open={bulkActionDialogOpen} onOpenChange={setBulkActionDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {bulkAction === "lock" && "Lock Users"}
              {bulkAction === "unlock" && "Unlock Users"}
              {bulkAction === "delete" && "Delete Users"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {bulkAction === "lock" &&
                `Are you sure you want to lock ${selectedUsers.size} user(s)? They won't be able to log in.`}
              {bulkAction === "unlock" &&
                `Are you sure you want to unlock ${selectedUsers.size} user(s)?`}
              {bulkAction === "delete" &&
                `Are you sure you want to delete ${selectedUsers.size} user(s)? This action cannot be undone.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkAction}
              className={bulkAction === "delete" ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : ""}
            >
              {bulkAction === "lock" && "Lock Users"}
              {bulkAction === "unlock" && "Unlock Users"}
              {bulkAction === "delete" && "Delete Users"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </AdminLayout>
  )
}
