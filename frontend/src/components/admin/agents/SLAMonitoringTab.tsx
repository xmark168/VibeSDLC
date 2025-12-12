import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, AlertTriangle, CheckCircle, XCircle } from "lucide-react"
import { useSLAStats, useSLASummary } from "@/queries/agents"
import { Progress } from "@/components/ui/progress"

export function SLAMonitoringTab() {
  const { data: stats, isLoading: statsLoading } = useSLAStats()
  const { data: summary, isLoading: summaryLoading } = useSLASummary()

  const isLoading = statsLoading || summaryLoading

  const getHealthBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" />Healthy</Badge>
      case "degraded":
        return <Badge className="bg-yellow-500"><AlertTriangle className="w-3 h-3 mr-1" />Degraded</Badge>
      case "critical":
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" />Critical</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
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

  const violationRate = stats?.violation_rate || 0
  const healthPercentage = 100 - (violationRate * 100)

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Health Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {getHealthBadge(summary?.health_status || "healthy")}
              <Progress 
                value={healthPercentage} 
                className="h-2 mt-2" 
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Checks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_checks?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-yellow-600">Violations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {stats?.total_violations || 0}
            </div>
            <div className="text-xs text-muted-foreground">
              {stats?.unacknowledged_violations || 0} unacknowledged
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600">Critical</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {stats?.critical_unacknowledged || 0}
            </div>
            <div className="text-xs text-muted-foreground">unacknowledged critical</div>
          </CardContent>
        </Card>
      </div>

      {/* Violations by Task Type */}
      <Card>
        <CardHeader>
          <CardTitle>Violations by Task Type</CardTitle>
          <CardDescription>
            SLA violations grouped by task type
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!stats?.violations_by_task_type || Object.keys(stats.violations_by_task_type).length === 0 ? (
            <div className="text-center text-muted-foreground py-6">
              <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
              No SLA violations recorded
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(stats.violations_by_task_type).map(([taskType, count]) => (
                <div key={taskType} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{taskType}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{count as number}</span>
                    <span className="text-muted-foreground text-sm">violations</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Configured Task Types */}
      <Card>
        <CardHeader>
          <CardTitle>Configured SLA Thresholds</CardTitle>
          <CardDescription>
            Task types with SLA monitoring enabled
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {stats?.configured_task_types?.map((taskType) => (
              <Badge key={taskType} variant="secondary">
                {taskType}
              </Badge>
            ))}
            {(!stats?.configured_task_types || stats.configured_task_types.length === 0) && (
              <span className="text-muted-foreground">No task types configured</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Top Violators */}
      {summary?.top_violators && summary.top_violators.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Top Violators</CardTitle>
            <CardDescription>
              Agents with the most SLA violations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {summary.top_violators.map((violator, index) => (
                <div key={violator.agent_id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">#{index + 1}</span>
                    <span className="font-mono text-xs">{violator.agent_id.slice(0, 8)}...</span>
                  </div>
                  <Badge variant={violator.count > 5 ? "destructive" : "secondary"}>
                    {violator.count} violations
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
