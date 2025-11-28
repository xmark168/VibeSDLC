import { useState } from "react"
import {
  Plus,
  Edit,
  Trash2,
  MoreVertical,
  Users,
  CheckCircle,
  XCircle,
  Filter,
  Loader2,
} from "lucide-react"
import type { PersonaWithUsageStats, RoleType } from "@/types/persona"
import { roleTypeLabels, roleTypeColors } from "@/types/persona"
import { usePersonasWithStats, useDeletePersona, useActivatePersona } from "@/queries/personas"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PersonaDialog } from "./dialogs/PersonaDialog"
import { formatDistanceToNow } from "date-fns"

export function PersonasTab() {
  const [roleFilter, setRoleFilter] = useState<string>("all")
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [personaToEdit, setPersonaToEdit] = useState<PersonaWithUsageStats | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [personaToDelete, setPersonaToDelete] = useState<PersonaWithUsageStats | null>(null)

  const { data: personas, isLoading, refetch } = usePersonasWithStats(
    roleFilter !== "all" ? roleFilter : undefined
  )
  const deletePersona = useDeletePersona()
  const activatePersona = useActivatePersona()

  const handleEdit = (persona: PersonaWithUsageStats) => {
    setPersonaToEdit(persona)
    setEditDialogOpen(true)
  }

  const handleDelete = async () => {
    if (!personaToDelete) return
    await deletePersona.mutateAsync({
      personaId: personaToDelete.id,
      hardDelete: false,
    })
    setDeleteDialogOpen(false)
    setPersonaToDelete(null)
    refetch()
  }

  const handleActivate = async (persona: PersonaWithUsageStats) => {
    await activatePersona.mutateAsync(persona.id)
    refetch()
  }

  const stats = personas
    ? {
        total: personas.length,
        active: personas.filter((p) => p.is_active).length,
        inactive: personas.filter((p) => !p.is_active).length,
        inUse: personas.filter((p) => p.active_agents_count > 0).length,
      }
    : { total: 0, active: 0, inactive: 0, inUse: 0 }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Persona Templates</h2>
          <p className="text-muted-foreground">
            Manage personality templates for agent diversity
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Create Persona
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Personas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inactive</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.inactive}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.inUse}</div>
            <p className="text-xs text-muted-foreground">
              {personas ? personas.reduce((sum, p) => sum + p.active_agents_count, 0) : 0} active agents
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Filter by Role:</span>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {Object.entries(roleTypeLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Personas Table */}
      <Card>
        <CardHeader>
          <CardTitle>Personas</CardTitle>
          <CardDescription>
            {personas?.length || 0} persona templates
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : personas?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No personas found</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="w-4 h-4 mr-2" />
                Create First Persona
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Role Type</TableHead>
                  <TableHead>Traits</TableHead>
                  <TableHead>Communication Style</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="w-[70px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {personas.map((persona) => (
                  <TableRow key={persona.id}>
                    <TableCell className="font-medium">{persona.name}</TableCell>
                    <TableCell>
                      <Badge
                        className={roleTypeColors[persona.role_type as RoleType]}
                        variant="outline"
                      >
                        {roleTypeLabels[persona.role_type as RoleType]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {persona.personality_traits.slice(0, 3).map((trait) => (
                          <Badge key={trait} variant="secondary" className="text-xs">
                            {trait}
                          </Badge>
                        ))}
                        {persona.personality_traits.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{persona.personality_traits.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[250px] truncate">
                      {persona.communication_style}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div className="font-medium">
                          {persona.active_agents_count} active
                        </div>
                        <div className="text-muted-foreground">
                          {persona.total_agents_created} total
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {persona.is_active ? (
                        <Badge variant="default" className="bg-green-500">
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(persona.updated_at), {
                        addSuffix: true,
                      })}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(persona)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          {!persona.is_active && (
                            <DropdownMenuItem onClick={() => handleActivate(persona)}>
                              <CheckCircle className="w-4 h-4 mr-2" />
                              Activate
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => {
                              setPersonaToDelete(persona)
                              setDeleteDialogOpen(true)
                            }}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            {persona.is_active ? "Deactivate" : "Delete"}
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
      <PersonaDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          refetch()
          setCreateDialogOpen(false)
        }}
      />

      <PersonaDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        persona={personaToEdit || undefined}
        onSuccess={() => {
          refetch()
          setEditDialogOpen(false)
          setPersonaToEdit(null)
        }}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {personaToDelete?.is_active ? "Deactivate" : "Delete"} Persona
            </AlertDialogTitle>
            <AlertDialogDescription>
              {personaToDelete?.is_active ? (
                <>
                  Are you sure you want to deactivate "{personaToDelete?.name}"? It will no
                  longer be available for new agents.
                  {personaToDelete?.active_agents_count > 0 && (
                    <span className="block mt-2 text-amber-500 font-medium">
                      Note: {personaToDelete.active_agents_count} active agents are currently
                      using this persona.
                    </span>
                  )}
                </>
              ) : (
                <>
                  Are you sure you want to permanently delete "{personaToDelete?.name}"?
                  This action cannot be undone.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive">
              {personaToDelete?.is_active ? "Deactivate" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
