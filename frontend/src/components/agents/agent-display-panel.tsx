import { useState } from "react"
import { cn } from "@/lib/utils"
import { AgentCard } from "./agent-card"
import { AgentDetailSheet } from "./agent-detail-sheet"
import { useAllAgentHealth, useAgentPools } from "@/queries/agents"
import type { AgentHealth, PoolResponse } from "@/apis/agents"
import {
  Bot,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Users,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

interface AgentDisplayPanelProps {
  className?: string
  compact?: boolean
}

export function AgentDisplayPanel({ className, compact = false }: AgentDisplayPanelProps) {
  const [selectedAgent, setSelectedAgent] = useState<{
    agent: AgentHealth
    poolName: string
  } | null>(null)
  const [expandedPools, setExpandedPools] = useState<Set<string>>(new Set())

  const {
    data: healthData,
    isLoading: healthLoading,
    refetch: refetchHealth,
    isRefetching,
  } = useAllAgentHealth({ refetchInterval: 30000 })

  const { data: poolsData, isLoading: poolsLoading } = useAgentPools({
    refetchInterval: 30000,
  })

  const isLoading = healthLoading || poolsLoading

  const togglePool = (poolName: string) => {
    setExpandedPools((prev) => {
      const next = new Set(prev)
      if (next.has(poolName)) {
        next.delete(poolName)
      } else {
        next.add(poolName)
      }
      return next
    })
  }

  // Calculate total counts
  const totalAgents = healthData
    ? Object.values(healthData).reduce((sum, agents) => sum + agents.length, 0)
    : 0
  const busyAgents = healthData
    ? Object.values(healthData)
        .flat()
        .filter((a) => a.state === "busy").length
    : 0
  const idleAgents = healthData
    ? Object.values(healthData)
        .flat()
        .filter((a) => a.state === "idle").length
    : 0

  if (compact) {
    return (
      <CompactAgentPanel
        healthData={healthData}
        isLoading={isLoading}
        onSelectAgent={(agent, poolName) => setSelectedAgent({ agent, poolName })}
      />
    )
  }

  return (
    <div className={cn("flex flex-col h-full bg-background", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Agents</h3>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {totalAgents}
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => refetchHealth()}
          disabled={isRefetching}
        >
          <RefreshCw className={cn("w-4 h-4", isRefetching && "animate-spin")} />
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-2 px-4 py-3 border-b bg-muted/30">
        <SummaryItem icon={Users} label="Total" value={totalAgents} />
        <SummaryItem
          icon={Bot}
          label="Idle"
          value={idleAgents}
          valueColor="text-green-500"
        />
        <SummaryItem
          icon={Loader2}
          label="Busy"
          value={busyAgents}
          valueColor="text-yellow-500"
          iconSpin={busyAgents > 0}
        />
      </div>

      {/* Agent List */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {isLoading ? (
            <AgentListSkeleton />
          ) : !healthData || Object.keys(healthData).length === 0 ? (
            <EmptyState />
          ) : (
            Object.entries(healthData).map(([poolName, agents]) => (
              <PoolGroup
                key={poolName}
                poolName={poolName}
                agents={agents}
                poolStats={poolsData?.find((p) => p.pool_name === poolName)}
                isExpanded={expandedPools.has(poolName)}
                onToggle={() => togglePool(poolName)}
                onSelectAgent={(agent) => setSelectedAgent({ agent, poolName })}
              />
            ))
          )}
        </div>
      </ScrollArea>

      {/* Detail Sheet */}
      <AgentDetailSheet
        agent={selectedAgent?.agent || null}
        poolName={selectedAgent?.poolName || ""}
        open={!!selectedAgent}
        onOpenChange={(open) => !open && setSelectedAgent(null)}
      />
    </div>
  )
}

function SummaryItem({
  icon: Icon,
  label,
  value,
  valueColor,
  iconSpin,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  valueColor?: string
  iconSpin?: boolean
}) {
  return (
    <div className="text-center">
      <div className="flex items-center justify-center gap-1">
        <Icon className={cn("w-3.5 h-3.5 text-muted-foreground", iconSpin && "animate-spin")} />
        <span className={cn("text-lg font-semibold", valueColor)}>{value}</span>
      </div>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

function PoolGroup({
  poolName,
  agents,
  poolStats,
  isExpanded,
  onToggle,
  onSelectAgent,
}: {
  poolName: string
  agents: AgentHealth[]
  poolStats?: PoolResponse
  isExpanded: boolean
  onToggle: () => void
  onSelectAgent: (agent: AgentHealth) => void
}) {
  // Auto-expand if not explicitly toggled
  const expanded = isExpanded || agents.length <= 3

  return (
    <Collapsible open={expanded} onOpenChange={onToggle}>
      <CollapsibleTrigger asChild>
        <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
            <span className="text-sm font-medium">{formatPoolName(poolName)}</span>
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {agents.length}
            </span>
          </div>
          {poolStats && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Load: {(poolStats.load * 100).toFixed(0)}%</span>
            </div>
          )}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 space-y-2 pl-6">
          {agents.map((agent) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              onClick={() => onSelectAgent(agent)}
              compact
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function CompactAgentPanel({
  healthData,
  isLoading,
  onSelectAgent,
}: {
  healthData: Record<string, AgentHealth[]> | undefined
  isLoading: boolean
  onSelectAgent: (agent: AgentHealth, poolName: string) => void
}) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!healthData || Object.keys(healthData).length === 0) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        No agents running
      </div>
    )
  }

  const allAgents = Object.entries(healthData).flatMap(([poolName, agents]) =>
    agents.map((agent) => ({ agent, poolName }))
  )

  return (
    <div className="p-2 space-y-1">
      {allAgents.slice(0, 5).map(({ agent, poolName }) => (
        <AgentCard
          key={agent.agent_id}
          agent={agent}
          onClick={() => onSelectAgent(agent, poolName)}
          compact
        />
      ))}
      {allAgents.length > 5 && (
        <div className="text-xs text-center text-muted-foreground pt-2">
          +{allAgents.length - 5} more agents
        </div>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <AlertCircle className="w-6 h-6 text-muted-foreground" />
      </div>
      <h4 className="text-sm font-medium mb-1">No Agents Running</h4>
      <p className="text-xs text-muted-foreground max-w-[200px]">
        Create an agent pool and spawn agents to see them here.
      </p>
    </div>
  )
}

function AgentListSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <div className="pl-6 space-y-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

function formatPoolName(poolName: string): string {
  return poolName
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Export index
export { AgentCard } from "./agent-card"
export { AgentStatusBadge, AgentStatusDot } from "./agent-status-badge"
export { AgentDetailSheet } from "./agent-detail-sheet"
