import { TrendingUp, Clock, Target, AlertTriangle, Activity, Calendar } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useFlowMetrics } from "@/queries/backlog-items"
import { useState } from "react"

interface FlowMetricsDashboardProps {
  projectId: string | undefined
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FlowMetricsDashboard({ projectId, open, onOpenChange }: FlowMetricsDashboardProps) {
  const [timeRange, setTimeRange] = useState<number>(30)
  const { data: metrics, isLoading } = useFlowMetrics(projectId, timeRange, open)

  const formatHours = (hours: number | null) => {
    if (hours === null) return "N/A"
    if (hours < 24) return `${hours.toFixed(1)}h`
    const days = (hours / 24).toFixed(1)
    return `${days}d`
  }

  const formatAge = (hours: number) => {
    if (hours < 24) return `${Math.round(hours)}h`
    const days = Math.floor(hours / 24)
    return `${days}d`
  }

  const getAgeSeverity = (hours: number) => {
    if (hours >= 120) return "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300"
    if (hours >= 72) return "bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300"
    return "bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300"
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Flow Metrics Dashboard
              </DialogTitle>
              <DialogDescription>
                Monitor your team's flow efficiency and identify bottlenecks
              </DialogDescription>
            </div>
            <Select
              value={timeRange.toString()}
              onValueChange={(value) => setTimeRange(parseInt(value, 10))}
            >
              <SelectTrigger className="w-32 h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="14">Last 14 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="60">Last 60 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </DialogHeader>

        <Separator />

        {isLoading ? (
          <div className="py-12 text-center text-sm text-muted-foreground">Loading metrics...</div>
        ) : metrics ? (
          <div className="space-y-6">
            {/* Key Metrics Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Cycle Time */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    Cycle Time
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatHours(metrics.avg_cycle_time_hours)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Started → Completed
                  </p>
                </CardContent>
              </Card>

              {/* Lead Time */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-purple-600" />
                    Lead Time
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatHours(metrics.avg_lead_time_hours)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Created → Completed
                  </p>
                </CardContent>
              </Card>

              {/* Throughput */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-600" />
                    Throughput
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {metrics.throughput_per_week.toFixed(1)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Items per week
                  </p>
                  <p className="text-xs text-muted-foreground">
                    ({metrics.total_completed} completed)
                  </p>
                </CardContent>
              </Card>

              {/* Work in Progress */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Target className="w-4 h-4 text-orange-600" />
                    Active WIP
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.work_in_progress}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    In Progress + Review
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Bottleneck Analysis */}
            {Object.keys(metrics.bottlenecks).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Bottleneck Analysis
                  </CardTitle>
                  <CardDescription>
                    Columns with highest average age indicate potential bottlenecks
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(metrics.bottlenecks)
                      .sort((a, b) => b[1].avg_age_hours - a[1].avg_age_hours)
                      .map(([status, data]) => (
                        <div key={status} className="flex items-center justify-between p-3 rounded-lg border">
                          <div className="flex items-center gap-3">
                            <Badge
                              variant="outline"
                              className={
                                status === "Todo"
                                  ? "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
                                  : status === "InProgress"
                                  ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                                  : "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
                              }
                            >
                              {status}
                            </Badge>
                            <div>
                              <div className="text-sm font-medium">
                                {data.count} item{data.count !== 1 ? "s" : ""}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                Avg age: {formatAge(data.avg_age_hours)}
                              </div>
                            </div>
                          </div>
                          {data.avg_age_hours >= 72 && (
                            <Badge variant="outline" className="bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300">
                              High
                            </Badge>
                          )}
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Aging Items */}
            {metrics.aging_items.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Aging Items
                  </CardTitle>
                  <CardDescription>
                    Items stuck in current status for more than 3 days ({metrics.aging_items.length} items)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {metrics.aging_items
                      .sort((a, b) => b.age_hours - a.age_hours)
                      .map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{item.title}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              Status: {item.status}
                            </div>
                          </div>
                          <Badge variant="outline" className={getAgeSeverity(item.age_hours)}>
                            {formatAge(item.age_hours)}
                          </Badge>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* No Data Message */}
            {metrics.total_completed === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <Activity className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-sm text-muted-foreground">
                    No completed items in the selected time range.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Complete some items to see flow metrics.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No metrics available
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
