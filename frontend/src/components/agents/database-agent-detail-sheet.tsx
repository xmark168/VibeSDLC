import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { AgentStatusBadge } from "./agent-status-badge"
import type { AgentPublic } from "@/client/types.gen"
import {
  Bot,
  Users,
  Sparkles,
  Target,
  ListChecks,
  Code,
  TestTube2,
  Calendar,
  Hash,
  Layers,
  Info,
  Activity,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface DatabaseAgentDetailSheetProps {
  agent: AgentPublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Helper function to convert snake_case to Title Case
const toTitleCase = (str: string): string => {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

// Helper function to format agent status
const formatStatus = (status: string): string => {
  const statusMap: Record<string, string> = {
    idle: "Idle",
    busy: "Busy",
    stopped: "Stopped",
    error: "Error",
  }
  return statusMap[status] || toTitleCase(status)
}

// Role descriptions and capabilities
const ROLE_INFO: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>
    description: string
    capabilities: string[]
    gradient: string
    bgColor: string
  }
> = {
  team_leader: {
    icon: Users,
    description:
      "Orchestrates the team, delegates tasks, and ensures project alignment with goals.",
    capabilities: [
      "Task delegation and coordination",
      "Project planning and oversight",
      "Team communication management",
      "Decision making and prioritization",
    ],
    gradient: "from-purple-500 to-pink-500",
    bgColor: "bg-purple-500/10",
  },
  business_analyst: {
    icon: Target,
    description:
      "Analyzes requirements, creates product specifications, and designs business flows.",
    capabilities: [
      "Requirements gathering and analysis",
      "Product brief creation",
      "Business flow design",
      "Epic and story creation",
      "Stakeholder communication",
    ],
    gradient: "from-blue-500 to-cyan-500",
    bgColor: "bg-blue-500/10",
  },
  developer: {
    icon: Code,
    description: "Implements features, writes code, and builds the product according to specifications.",
    capabilities: [
      "Feature implementation",
      "Code writing and review",
      "Technical problem solving",
      "Code quality maintenance",
      "Integration and deployment",
    ],
    gradient: "from-green-500 to-emerald-500",
    bgColor: "bg-green-500/10",
  },
  tester: {
    icon: TestTube2,
    description: "Tests features, identifies bugs, and ensures quality standards are met.",
    capabilities: [
      "Test plan creation",
      "Feature testing and validation",
      "Bug identification and reporting",
      "Quality assurance",
      "Test automation",
    ],
    gradient: "from-orange-500 to-red-500",
    bgColor: "bg-orange-500/10",
  },
}

export function DatabaseAgentDetailSheet({
  agent,
  open,
  onOpenChange,
}: DatabaseAgentDetailSheetProps) {
  if (!agent) return null

  const roleInfo = ROLE_INFO[agent.role_type] || {
    icon: Bot,
    description: "AI agent assisting with project tasks",
    capabilities: [],
    gradient: "from-gray-500 to-slate-500",
    bgColor: "bg-gray-500/10",
  }

  const RoleIcon = roleInfo.icon

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header with gradient background */}
        <div className={cn("relative -mx-6 -mt-6 px-6 pt-6 pb-6 rounded-t-lg", roleInfo.bgColor)}>
          <div className={cn("absolute inset-0 bg-gradient-to-br opacity-10 rounded-t-lg", roleInfo.gradient)} />

          <DialogHeader className="relative">
            <div className="flex items-start gap-4">
              <div className={cn(
                "w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg bg-gradient-to-br",
                roleInfo.gradient
              )}>
                <RoleIcon className="w-8 h-8 text-white" />
              </div>

              <div className="flex-1">
                <DialogTitle className="text-2xl font-bold mb-1">
                  {agent.human_name}
                </DialogTitle>
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  {agent.name}
                </p>
                <AgentStatusBadge status={agent.status as any} size="md" />
              </div>
            </div>
          </DialogHeader>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-4 mx-6">
            <TabsTrigger value="overview" className="gap-2">
              <Info className="w-4 h-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="capabilities" className="gap-2">
              <Sparkles className="w-4 h-4" />
              <span className="hidden sm:inline">Capabilities</span>
            </TabsTrigger>
            <TabsTrigger value="logs" className="gap-2">
              <Activity className="w-4 h-4" />
              <span className="hidden sm:inline">Logs</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">Settings</span>
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto px-6 pt-4">
            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-6 mt-0">
              {/* Role Description */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", roleInfo.bgColor)}>
                    <Target className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-lg">Role Description</h3>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed pl-10">
                  {roleInfo.description}
                </p>
              </div>

              <Separator />

              {/* Quick Stats */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", roleInfo.bgColor)}>
                    <Activity className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-lg">Quick Stats</h3>
                </div>
                <div className="pl-10 grid grid-cols-2 gap-4">
                  <StatCard label="Total Executions" value="0" />
                  <StatCard label="Success Rate" value="N/A" />
                  <StatCard label="Avg Duration" value="N/A" />
                  <StatCard label="Last Active" value="N/A" />
                </div>
              </div>
            </TabsContent>

            {/* Capabilities Tab */}
            <TabsContent value="capabilities" className="space-y-6 mt-0">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", roleInfo.bgColor)}>
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-lg">Agent Capabilities</h3>
                </div>
                <p className="text-sm text-muted-foreground pl-10">
                  This agent is specialized in the following areas:
                </p>
              </div>

              <div className="space-y-2">
                {roleInfo.capabilities.map((capability, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center justify-center w-6 h-6 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex-shrink-0 mt-0.5">
                      <span className="text-xs font-semibold text-primary">{index + 1}</span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{capability}</p>
                    </div>
                  </div>
                ))}
              </div>

              <Separator />

              <div className="p-4 rounded-lg bg-muted/20 border border-dashed">
                <p className="text-sm text-muted-foreground">
                  <strong>Note:</strong> Agent capabilities are continuously improved through learning and updates.
                </p>
              </div>
            </TabsContent>

            {/* Logs Tab */}
            <TabsContent value="logs" className="space-y-6 mt-0">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", roleInfo.bgColor)}>
                    <ListChecks className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-lg">Execution History</h3>
                </div>
                <p className="text-sm text-muted-foreground pl-10">
                  Recent agent executions and activity logs
                </p>
              </div>

              <div className="p-8 rounded-lg border border-dashed border-muted-foreground/30 text-center">
                <Activity className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  No execution logs yet
                </p>
                <p className="text-xs text-muted-foreground">
                  Logs will appear here when the agent starts executing tasks
                </p>
              </div>

              {/* Future: Real logs will be displayed here */}
              {/* Example log structure:
              <div className="space-y-2">
                <LogEntry
                  timestamp="2024-01-15 10:30:45"
                  status="success"
                  message="Task completed successfully"
                  duration="2.5s"
                />
              </div>
              */}
            </TabsContent>

            {/* Settings/Info Tab */}
            <TabsContent value="settings" className="space-y-6 mt-0">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", roleInfo.bgColor)}>
                    <Layers className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-lg">Agent Information</h3>
                </div>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <InfoCard
                    icon={Hash}
                    label="Agent ID"
                    value={agent.id.slice(0, 8)}
                    mono
                  />
                  <InfoCard
                    icon={Layers}
                    label="Project ID"
                    value={agent.project_id.slice(0, 8)}
                    mono
                  />
                  <InfoCard
                    icon={Calendar}
                    label="Created"
                    value={new Date(agent.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  />
                  <InfoCard
                    icon={Calendar}
                    label="Updated"
                    value={new Date(agent.updated_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <h4 className="text-sm font-semibold">Configuration</h4>
                <div className="space-y-2">
                  <ConfigItem label="Role Type" value={toTitleCase(agent.role_type)} />
                  <ConfigItem label="Agent Type" value={agent.agent_type ? toTitleCase(agent.agent_type) : "N/A"} />
                  <div className="flex items-center justify-between p-2 rounded-lg bg-muted/20">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <AgentStatusBadge status={agent.status as any} size="sm" />
                  </div>
                </div>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

// Helper component for info cards
function InfoCard({
  icon: Icon,
  label,
  value,
  mono = false,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
      </div>
      <p className={cn("text-sm font-medium", mono && "font-mono")}>
        {value}
      </p>
    </div>
  )
}

// Helper component for stat cards
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-muted/30">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  )
}

// Helper component for config items
function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/20">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}
