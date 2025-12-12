import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Play, Square, Thermometer, Users, AlertTriangle } from "lucide-react"
import { toast } from "@/lib/toast"
import { useWarmPoolStatus, useStartWarmPool, useStopWarmPool } from "@/queries/agents"
import { Progress } from "@/components/ui/progress"

export function WarmPoolTab() {
  const { data: status, isLoading } = useWarmPoolStatus()
  const startWarmPool = useStartWarmPool()
  const stopWarmPool = useStopWarmPool()

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

  const handleStart = () => {
    startWarmPool.mutate(undefined, {
      onSuccess: (data) => toast.success(data.message),
      onError: (e) => toast.error(`Failed: ${e.message}`),
    })
  }

  const handleStop = () => {
    stopWarmPool.mutate(undefined, {
      onSuccess: (data) => toast.success(data.message),
      onError: (e) => toast.error(`Failed: ${e.message}`),
    })
  }

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Thermometer className="w-5 h-5" />
                Warm Pool Manager
              </CardTitle>
              <CardDescription>
                Pre-spawn agents to reduce latency for new task assignments
              </CardDescription>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant={status?.running ? "default" : "secondary"}>
                {status?.running ? "Running" : "Stopped"}
              </Badge>
              {status?.running ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStop}
                  disabled={stopWarmPool.isPending}
                >
                  {stopWarmPool.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  Stop
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={handleStart}
                  disabled={startWarmPool.isPending}
                >
                  {startWarmPool.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Start
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold">
                {status?.health_percentage?.toFixed(1) || 100}%
              </div>
              <Progress value={status?.health_percentage || 100} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Required</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.total_required || 0}</div>
            <div className="text-xs text-muted-foreground">minimum agents</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Available</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {status?.total_available || 0}
            </div>
            <div className="text-xs text-muted-foreground">idle agents</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Deficit</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(status?.deficit || 0) > 0 ? "text-red-600" : "text-green-600"}`}>
              {status?.deficit || 0}
            </div>
            <div className="text-xs text-muted-foreground">agents needed</div>
          </CardContent>
        </Card>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Spawned</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.total_spawned || 0}</div>
            <div className="text-xs text-muted-foreground">
              agents spawned by warm pool
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Spawn Failures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(status?.spawn_failures || 0) > 0 ? "text-red-600" : ""}`}>
              {status?.spawn_failures || 0}
            </div>
            <div className="text-xs text-muted-foreground">failed spawn attempts</div>
          </CardContent>
        </Card>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Minimum Agents Configuration</CardTitle>
          <CardDescription>
            Target number of idle agents to maintain per role type
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!status?.min_agents_config || Object.keys(status.min_agents_config).length === 0 ? (
            <div className="text-center text-muted-foreground py-6">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-yellow-500" />
              No minimum agents configured. Update config.py to set warm pool targets.
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(status.min_agents_config).map(([roleType, minCount]) => {
                const currentIdle = status.current_idle_counts?.[roleType] || 0
                const progress = minCount > 0 ? (currentIdle / minCount) * 100 : 100
                const isSufficient = currentIdle >= minCount

                return (
                  <div key={roleType} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Users className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium">{roleType}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={isSufficient ? "text-green-600" : "text-yellow-600"}>
                          {currentIdle}
                        </span>
                        <span className="text-muted-foreground">/</span>
                        <span>{minCount}</span>
                        <Badge variant={isSufficient ? "default" : "secondary"}>
                          {isSufficient ? "OK" : "Low"}
                        </Badge>
                      </div>
                    </div>
                    <Progress 
                      value={Math.min(progress, 100)} 
                      className={`h-2 ${!isSufficient ? "[&>div]:bg-yellow-500" : ""}`}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Last Check */}
      {status?.last_check && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Last Check:</span>
              <span>{new Date(status.last_check).toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-muted-foreground">Check Interval:</span>
              <span>{status.check_interval}s</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
