import { useState } from "react"
import {
  Plus,
  Trash2,
  Play,
  Pause,
  Clock,
  Activity,
  Zap,
  MoreVertical,
  Loader2,
  Settings,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { toast } from "sonner"
import {
  useScalingRules,
  useCreateScalingRule,
  useDeleteScalingRule,
  useToggleScalingRule,
  useTriggerScalingRule,
} from "@/queries/agents"
import type { AutoScalingRule, AutoScalingRuleCreate, PoolResponse } from "@/types"

interface ScalingTabProps {
  pools: PoolResponse[]
}

const triggerTypeLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  schedule: { label: "Schedule", icon: <Clock className="w-4 h-4" /> },
  load: { label: "Load-based", icon: <Activity className="w-4 h-4" /> },
  queue_depth: { label: "Queue Depth", icon: <Zap className="w-4 h-4" /> },
}

const actionLabels: Record<string, string> = {
  scale_up: "Scale Up",
  scale_down: "Scale Down",
  set_count: "Set Count",
}

export function ScalingTab({ pools }: ScalingTabProps) {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [formData, setFormData] = useState<Partial<AutoScalingRuleCreate>>({
    name: "",
    pool_name: pools[0]?.pool_name || "",
    trigger_type: "schedule",
    action: "scale_up",
    scale_amount: 1,
    min_agents: 1,
    max_agents: 10,
    cooldown_seconds: 300,
  })

  const { data: rules, isLoading } = useScalingRules()
  const createRule = useCreateScalingRule()
  const deleteRule = useDeleteScalingRule()
  const toggleRule = useToggleScalingRule()
  const triggerRule = useTriggerScalingRule()

  const handleCreate = async () => {
    if (!formData.name || !formData.pool_name) {
      toast.error("Name and Pool are required")
      return
    }

    try {
      await createRule.mutateAsync(formData as AutoScalingRuleCreate)
      toast.success("Scaling rule created")
      setCreateDialogOpen(false)
      setFormData({
        name: "",
        pool_name: pools[0]?.pool_name || "",
        trigger_type: "schedule",
        action: "scale_up",
        scale_amount: 1,
        min_agents: 1,
        max_agents: 10,
        cooldown_seconds: 300,
      })
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleDelete = async (rule: AutoScalingRule) => {
    if (!rule.id) return
    if (!confirm(`Delete rule "${rule.name}"?`)) return

    try {
      await deleteRule.mutateAsync(rule.id)
      toast.success("Rule deleted")
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleToggle = async (rule: AutoScalingRule) => {
    if (!rule.id) return

    try {
      await toggleRule.mutateAsync(rule.id)
      toast.success(`Rule ${rule.enabled ? "disabled" : "enabled"}`)
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleTrigger = async (rule: AutoScalingRule) => {
    if (!rule.id) return

    try {
      const result = await triggerRule.mutateAsync(rule.id)
      toast.success(result.message)
    } catch (error: any) {
      toast.error(error.message)
    }
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
              <CardTitle>Auto-scaling Rules</CardTitle>
              <CardDescription>
                Configure automatic scaling based on schedule or load metrics
              </CardDescription>
            </div>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!rules || rules.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No scaling rules configured. Add a rule to enable auto-scaling.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Pool</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Limits</TableHead>
                  <TableHead>Last Triggered</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell>
                      <Switch
                        checked={rule.enabled}
                        onCheckedChange={() => handleToggle(rule)}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>{rule.pool_name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {triggerTypeLabels[rule.trigger_type]?.icon}
                        <span>{triggerTypeLabels[rule.trigger_type]?.label}</span>
                        {rule.cron_expression && (
                          <Badge variant="outline" className="ml-1">
                            {rule.cron_expression}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={rule.action === "scale_up" ? "default" : "secondary"}>
                        {actionLabels[rule.action]}
                        {rule.action === "set_count" && rule.target_count
                          ? ` → ${rule.target_count}`
                          : ` ${rule.scale_amount}`}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {rule.min_agents} - {rule.max_agents}
                    </TableCell>
                    <TableCell>
                      {rule.last_triggered
                        ? new Date(rule.last_triggered).toLocaleString()
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem onClick={() => handleTrigger(rule)}>
                            <Play className="w-4 h-4 mr-2" />
                            Trigger Now
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleToggle(rule)}>
                            {rule.enabled ? (
                              <>
                                <Pause className="w-4 h-4 mr-2" />
                                Disable
                              </>
                            ) : (
                              <>
                                <Play className="w-4 h-4 mr-2" />
                                Enable
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDelete(rule)}
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

      {/* Create Rule Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Scaling Rule</DialogTitle>
            <DialogDescription>
              Add a new auto-scaling rule for agent management
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Rule Name</Label>
              <Input
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Scale up during business hours"
              />
            </div>

            <div className="space-y-2">
              <Label>Pool</Label>
              <Select
                value={formData.pool_name}
                onValueChange={(v) => setFormData({ ...formData, pool_name: v })}
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
              <Label>Trigger Type</Label>
              <Select
                value={formData.trigger_type}
                onValueChange={(v: any) => setFormData({ ...formData, trigger_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="schedule">Schedule (Cron)</SelectItem>
                  <SelectItem value="load">Load-based</SelectItem>
                  <SelectItem value="queue_depth">Queue Depth</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.trigger_type === "schedule" && (
              <div className="space-y-2">
                <Label>Cron Expression</Label>
                <Input
                  value={formData.cron_expression || ""}
                  onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                  placeholder="0 9 * * 1-5 (9 AM weekdays)"
                />
              </div>
            )}

            {(formData.trigger_type === "load" || formData.trigger_type === "queue_depth") && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>High Threshold</Label>
                  <Input
                    type="number"
                    value={formData.threshold_high || ""}
                    onChange={(e) => setFormData({ ...formData, threshold_high: parseFloat(e.target.value) })}
                    placeholder="80"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Low Threshold</Label>
                  <Input
                    type="number"
                    value={formData.threshold_low || ""}
                    onChange={(e) => setFormData({ ...formData, threshold_low: parseFloat(e.target.value) })}
                    placeholder="20"
                  />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label>Action</Label>
              <Select
                value={formData.action}
                onValueChange={(v: any) => setFormData({ ...formData, action: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="scale_up">Scale Up</SelectItem>
                  <SelectItem value="scale_down">Scale Down</SelectItem>
                  <SelectItem value="set_count">Set Count</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.action === "set_count" ? (
              <div className="space-y-2">
                <Label>Target Count</Label>
                <Input
                  type="number"
                  value={formData.target_count || ""}
                  onChange={(e) => setFormData({ ...formData, target_count: parseInt(e.target.value) })}
                  placeholder="5"
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label>Scale Amount</Label>
                <Input
                  type="number"
                  value={formData.scale_amount || 1}
                  onChange={(e) => setFormData({ ...formData, scale_amount: parseInt(e.target.value) })}
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Min Agents</Label>
                <Input
                  type="number"
                  value={formData.min_agents || 1}
                  onChange={(e) => setFormData({ ...formData, min_agents: parseInt(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Max Agents</Label>
                <Input
                  type="number"
                  value={formData.max_agents || 10}
                  onChange={(e) => setFormData({ ...formData, max_agents: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={createRule.isPending}>
              {createRule.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
