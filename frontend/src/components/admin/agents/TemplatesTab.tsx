import { useQuery } from "@tanstack/react-query"
import {
  Clock,
  Copy,
  FileCode,
  Loader2,
  MoreVertical,
  Play,
  Plus,
  Trash2,
  User,
} from "lucide-react"
import { useState } from "react"
import { projectsApi } from "@/apis/projects"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/lib/toast"
import {
  useCreateTemplate,
  useDeleteTemplate,
  useDuplicateTemplate,
  useSpawnFromTemplate,
  useTemplates,
} from "@/queries/agents"
import type { AgentTemplate, AgentTemplateCreate, PoolResponse } from "@/types"

interface TemplatesTabProps {
  pools: PoolResponse[]
  projectId?: string
}

const roleTypeLabels: Record<string, string> = {
  team_leader: "Team Leader",
  developer: "Developer",
  tester: "Tester",
  business_analyst: "Business Analyst",
}

export function TemplatesTab({ pools, projectId }: TemplatesTabProps) {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false)
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false)
  const [selectedTemplate, setSelectedTemplate] =
    useState<AgentTemplate | null>(null)
  const [spawnCount, setSpawnCount] = useState(1)
  const [duplicateName, setDuplicateName] = useState("")
  const [selectedProjectId, setSelectedProjectId] = useState(projectId || "")

  // Fetch projects for spawn dialog
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list({ page: 1, pageSize: 100 }),
  })
  const [formData, setFormData] = useState<Partial<AgentTemplateCreate>>({
    name: "",
    description: "",
    role_type: "developer",
    pool_name: pools[0]?.pool_name || "universal_pool",
    tags: [],
  })

  const { data: templates, isLoading } = useTemplates()
  const createTemplate = useCreateTemplate()
  const deleteTemplate = useDeleteTemplate()
  const spawnFromTemplate = useSpawnFromTemplate()
  const duplicateTemplate = useDuplicateTemplate()

  const handleCreate = async () => {
    if (!formData.name || !formData.role_type) {
      toast.error("Name and Role Type are required")
      return
    }

    try {
      await createTemplate.mutateAsync(formData as AgentTemplateCreate)
      toast.success("Template created")
      setCreateDialogOpen(false)
      setFormData({
        name: "",
        description: "",
        role_type: "developer",
        pool_name: pools[0]?.pool_name || "universal_pool",
        tags: [],
      })
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleDelete = async (template: AgentTemplate) => {
    if (!template.id) return
    if (!confirm(`Delete template "${template.name}"?`)) return

    try {
      await deleteTemplate.mutateAsync(template.id)
      toast.success("Template deleted")
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleSpawn = async () => {
    if (!selectedTemplate?.id || !selectedProjectId) {
      toast.error("Please select a project")
      return
    }

    try {
      const result = await spawnFromTemplate.mutateAsync({
        templateId: selectedTemplate.id,
        projectId: selectedProjectId,
        count: spawnCount,
      })
      toast.success(result.message)
      setSpawnDialogOpen(false)
      setSelectedTemplate(null)
      setSpawnCount(1)
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleDuplicate = async () => {
    if (!selectedTemplate?.id || !duplicateName) {
      toast.error("Name is required")
      return
    }

    try {
      await duplicateTemplate.mutateAsync({
        templateId: selectedTemplate.id,
        newName: duplicateName,
      })
      toast.success("Template duplicated")
      setDuplicateDialogOpen(false)
      setSelectedTemplate(null)
      setDuplicateName("")
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const openSpawnDialog = (template: AgentTemplate) => {
    setSelectedTemplate(template)
    setSpawnDialogOpen(true)
  }

  const openDuplicateDialog = (template: AgentTemplate) => {
    setSelectedTemplate(template)
    setDuplicateName(`${template.name} (Copy)`)
    setDuplicateDialogOpen(true)
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Agent Templates</CardTitle>
              <CardDescription>
                Save and reuse agent configurations for quick deployment
              </CardDescription>
            </div>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Template
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!templates || templates.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No templates created yet. Create a template to save agent
              configurations.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Pool</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Use Count</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{template.name}</div>
                          {template.description && (
                            <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {template.description}
                            </div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {roleTypeLabels[template.role_type] ||
                          template.role_type}
                      </Badge>
                    </TableCell>
                    <TableCell>{template.pool_name}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {template.tags.slice(0, 3).map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-xs"
                          >
                            {tag}
                          </Badge>
                        ))}
                        {template.tags.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{template.tags.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{template.use_count}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <User className="w-3 h-3" />
                        {template.created_by || "Unknown"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {template.created_at
                          ? new Date(template.created_at).toLocaleDateString()
                          : "N/A"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem
                            onClick={() => openSpawnDialog(template)}
                          >
                            <Play className="w-4 h-4 mr-2" />
                            Spawn Agents
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => openDuplicateDialog(template)}
                          >
                            <Copy className="w-4 h-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDelete(template)}
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

      {/* Create Template Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Agent Template</DialogTitle>
            <DialogDescription>
              Save a configuration as a reusable template
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Template Name</Label>
              <Input
                value={formData.name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., High Performance Developer"
              />
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={formData.description || ""}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Describe what this template is for..."
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label>Role Type</Label>
              <Select
                value={formData.role_type}
                onValueChange={(v) =>
                  setFormData({ ...formData, role_type: v })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="team_leader">Team Leader</SelectItem>
                  <SelectItem value="developer">Developer</SelectItem>
                  <SelectItem value="tester">Tester</SelectItem>
                  <SelectItem value="business_analyst">
                    Business Analyst
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Pool</Label>
              <Select
                value={formData.pool_name}
                onValueChange={(v) =>
                  setFormData({ ...formData, pool_name: v })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {pools.map((pool) => (
                    <SelectItem key={pool.pool_name} value={pool.pool_name}>
                      {pool.pool_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Tags (comma-separated)</Label>
              <Input
                value={formData.tags?.join(", ") || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    tags: e.target.value
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="production, high-priority"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={createTemplate.isPending}>
              {createTemplate.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Spawn Dialog */}
      <Dialog open={spawnDialogOpen} onOpenChange={setSpawnDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Spawn from Template</DialogTitle>
            <DialogDescription>
              Spawn agents using "{selectedTemplate?.name}"
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Project</Label>
              <Select
                value={selectedProjectId}
                onValueChange={setSelectedProjectId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select project" />
                </SelectTrigger>
                <SelectContent>
                  {projects?.data?.map((project: any) => (
                    <SelectItem key={project.id} value={project.id}>
                      {project.name} ({project.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Number of Agents</Label>
              <Input
                type="number"
                min={1}
                max={10}
                value={spawnCount}
                onChange={(e) =>
                  setSpawnCount(parseInt(e.target.value, 10) || 1)
                }
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSpawnDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSpawn}
              disabled={spawnFromTemplate.isPending || !selectedProjectId}
            >
              {spawnFromTemplate.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Spawn
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Duplicate Dialog */}
      <Dialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Duplicate Template</DialogTitle>
            <DialogDescription>
              Create a copy of "{selectedTemplate?.name}"
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>New Template Name</Label>
              <Input
                value={duplicateName}
                onChange={(e) => setDuplicateName(e.target.value)}
                placeholder="Enter new name"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDuplicateDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDuplicate}
              disabled={duplicateTemplate.isPending}
            >
              {duplicateTemplate.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Duplicate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
