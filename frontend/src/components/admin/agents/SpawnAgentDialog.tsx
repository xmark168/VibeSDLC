import { useQuery } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useState } from "react"
import { projectsApi } from "@/apis/projects"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/lib/toast"
import { useSpawnAgent } from "@/queries/agents"

interface SpawnAgentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  poolName: string
}

const roleTypes = [
  { value: "team_leader", label: "Team Leader" },
  { value: "developer", label: "Developer" },
  { value: "tester", label: "Tester" },
  { value: "business_analyst", label: "Business Analyst" },
]

export function SpawnAgentDialog({
  open,
  onOpenChange,
  poolName,
}: SpawnAgentDialogProps) {
  const [projectId, setProjectId] = useState("")
  const [roleType, setRoleType] = useState("")

  const spawnAgent = useSpawnAgent()

  // Fetch projects
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list({ page: 1, pageSize: 100 }),
  })

  const handleSpawn = async () => {
    if (!projectId || !roleType) {
      toast.error("Please select project and role type")
      return
    }

    try {
      const result = await spawnAgent.mutateAsync({
        project_id: projectId,
        role_type: roleType,
        pool_name: poolName,
      })
      toast.success(`Agent ${result.agent_id.slice(0, 8)} spawned`)
      onOpenChange(false)
      setProjectId("")
      setRoleType("")
    } catch (error: any) {
      toast.error(`Failed to spawn: ${error.message}`)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Spawn New Agent</DialogTitle>
          <DialogDescription>
            Spawn a new agent in pool: {poolName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Project</Label>
            <Select value={projectId} onValueChange={setProjectId}>
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
            <Label>Role Type</Label>
            <Select value={roleType} onValueChange={setRoleType}>
              <SelectTrigger>
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                {roleTypes.map((role) => (
                  <SelectItem key={role.value} value={role.value}>
                    {role.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSpawn} disabled={spawnAgent.isPending}>
            {spawnAgent.isPending && (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            )}
            Spawn Agent
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
