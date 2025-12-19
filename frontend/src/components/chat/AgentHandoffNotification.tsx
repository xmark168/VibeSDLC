import { ArrowRight, Crown } from "lucide-react"
import { Card } from "@/components/ui/card"

interface AgentHandoffNotificationProps {
  previousAgent?: string
  newAgent: string
  reason: string
  timestamp: string
}

export function AgentHandoffNotification({
  previousAgent,
  newAgent,
  reason,
  timestamp,
}: AgentHandoffNotificationProps) {
  const reasonText: Record<string, string> = {
    task_started: "started working on this task",
    delegated: "was delegated this task",
    completed_handoff: "took over after previous agent completed",
  }

  const displayReason = reasonText[reason] || reason

  return (
    <Card className="border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20 p-3 my-2">
      <div className="flex items-center gap-2 text-sm">
        <Crown className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />

        {previousAgent && (
          <>
            <span className="text-muted-foreground">{previousAgent}</span>
            <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </>
        )}

        <span className="font-semibold text-yellow-700 dark:text-yellow-300">
          {newAgent}
        </span>

        <span className="text-muted-foreground">{displayReason}</span>

        <span className="text-xs text-muted-foreground ml-auto flex-shrink-0">
          {new Date(timestamp).toLocaleTimeString()}
        </span>
      </div>
    </Card>
  )
}
