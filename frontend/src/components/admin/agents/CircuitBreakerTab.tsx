import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { RefreshCw, Loader2, ShieldCheck, ShieldAlert, ShieldX, RotateCcw } from "lucide-react"
import { toast } from "@/lib/toast"
import { useCircuitBreakers, useCircuitBreakerSummary, useResetAllCircuitBreakers } from "@/queries/agents"
import { Progress } from "@/components/ui/progress"

export function CircuitBreakerTab() {
  const { data: breakers, isLoading, refetch } = useCircuitBreakers()
  const { data: summary } = useCircuitBreakerSummary()
  const resetAll = useResetAllCircuitBreakers()

  const getStateBadge = (state: string) => {
    switch (state) {
      case "closed":
        return <Badge className="bg-green-500"><ShieldCheck className="w-3 h-3 mr-1" />Closed</Badge>
      case "open":
        return <Badge variant="destructive"><ShieldX className="w-3 h-3 mr-1" />Open</Badge>
      case "half_open":
        return <Badge className="bg-yellow-500"><ShieldAlert className="w-3 h-3 mr-1" />Half Open</Badge>
      default:
        return <Badge variant="outline">{state}</Badge>
    }
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
    return `${(seconds / 3600).toFixed(1)}h`
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
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Breakers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_breakers || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-600">Closed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{summary?.closed || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600">Open</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary?.open || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold">{summary?.health_percentage?.toFixed(1) || 100}%</div>
              <Progress value={summary?.health_percentage || 100} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Breakers Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Circuit Breakers</CardTitle>
              <CardDescription>
                Monitor and manage circuit breaker states for all agents
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  resetAll.mutate(undefined, {
                    onSuccess: (data) => toast.success(data.message),
                    onError: (e) => toast.error(`Failed: ${e.message}`),
                  })
                }}
                disabled={resetAll.isPending || !summary?.total_breakers}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {!breakers || breakers.length === 0 ? (
            <div className="text-center text-muted-foreground py-6">
              No circuit breakers active. Breakers are created when agents are spawned.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent ID</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Failures</TableHead>
                  <TableHead>Successes</TableHead>
                  <TableHead>Total Opens</TableHead>
                  <TableHead>Time in State</TableHead>
                  <TableHead>Last Failure</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breakers.map((breaker) => (
                  <TableRow key={breaker.agent_id}>
                    <TableCell className="font-mono text-xs">
                      {breaker.agent_id.slice(0, 8)}...
                    </TableCell>
                    <TableCell>{getStateBadge(breaker.state)}</TableCell>
                    <TableCell>
                      <span className={breaker.failure_count > 0 ? "text-red-600 font-medium" : ""}>
                        {breaker.failure_count}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-green-600">{breaker.success_count}</span>
                    </TableCell>
                    <TableCell>{breaker.total_opens}</TableCell>
                    <TableCell>{formatTime(breaker.time_in_state_seconds)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {breaker.last_failure_time
                        ? new Date(breaker.last_failure_time).toLocaleString()
                        : "Never"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
