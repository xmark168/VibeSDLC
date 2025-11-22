import { useState } from "react"
import { AlertOctagon, TrendingUp, X, Info } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"

interface BottleneckData {
  column: string
  avg_age_hours: number
  count: number
}

interface BottleneckAlertProps {
  bottlenecks?: Record<string, { avg_age_hours: number; count: number }>
  threshold?: number // hours threshold to show alert (default: 48)
}

export function BottleneckAlert({
  bottlenecks = {},
  threshold = 48,
}: BottleneckAlertProps) {
  const [isDismissed, setIsDismissed] = useState(false)

  const formatAge = (hours: number) => {
    const days = Math.floor(hours / 24)
    const remainingHours = Math.floor(hours % 24)

    if (days > 0) {
      return `${days}d ${remainingHours}h`
    }
    return `${Math.round(hours)}h`
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "inprogress":
      case "in_progress":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "review":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Convert bottlenecks to array and filter by threshold
  const bottleneckList: BottleneckData[] = Object.entries(bottlenecks)
    .map(([column, data]) => ({
      column,
      avg_age_hours: data.avg_age_hours,
      count: data.count,
    }))
    .filter((b) => b.avg_age_hours >= threshold)
    .sort((a, b) => b.avg_age_hours - a.avg_age_hours)

  // Don't show if dismissed or no bottlenecks
  if (isDismissed || bottleneckList.length === 0) {
    return null
  }

  const primaryBottleneck = bottleneckList[0]
  const maxAge = Math.max(...bottleneckList.map((b) => b.avg_age_hours))

  const getSeverityColor = (avgAge: number) => {
    if (avgAge >= 120) return { bg: "bg-red-500", text: "text-red-700", border: "border-red-200" }
    if (avgAge >= 72) return { bg: "bg-orange-500", text: "text-orange-700", border: "border-orange-200" }
    return { bg: "bg-yellow-500", text: "text-yellow-700", border: "border-yellow-200" }
  }

  const severityColor = getSeverityColor(primaryBottleneck.avg_age_hours)

  return (
    <Alert className={`mb-4 ${severityColor.border} bg-red-50 dark:bg-red-950/20`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1">
          <AlertOctagon className={`h-5 w-5 ${severityColor.text} mt-0.5`} />
          <div className="flex-1">
            <AlertDescription className="text-red-900 dark:text-red-200">
              <div className="font-semibold flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4" />
                Bottleneck Detected
              </div>
              <div className="text-sm text-red-700 dark:text-red-300 mb-3">
                Items are taking longer than usual in the following column{bottleneckList.length > 1 ? "s" : ""}:
              </div>

              <div className="space-y-3">
                {bottleneckList.map((bottleneck) => {
                  const severity = getSeverityColor(bottleneck.avg_age_hours)
                  const percentage = (bottleneck.avg_age_hours / maxAge) * 100

                  return (
                    <div
                      key={bottleneck.column}
                      className="p-3 rounded-md bg-white dark:bg-gray-900 border border-red-200 dark:border-red-900"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className={getStatusBadgeColor(bottleneck.column)}
                          >
                            {bottleneck.column}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {bottleneck.count} item{bottleneck.count !== 1 ? "s" : ""}
                          </span>
                        </div>
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            bottleneck.avg_age_hours >= 120
                              ? "bg-red-100 text-red-700 border-red-300"
                              : bottleneck.avg_age_hours >= 72
                              ? "bg-orange-100 text-orange-700 border-orange-300"
                              : "bg-yellow-100 text-yellow-700 border-yellow-300"
                          }`}
                        >
                          Avg: {formatAge(bottleneck.avg_age_hours)}
                        </Badge>
                      </div>
                      <Progress
                        value={percentage}
                        className="h-2"
                        indicatorClassName={severity.bg}
                      />
                    </div>
                  )
                })}
              </div>

              <div className="mt-3 p-2 rounded-md bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900">
                <div className="flex items-start gap-2 text-xs text-blue-700 dark:text-blue-300">
                  <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <strong>Recommendation:</strong> Review items in this column to identify and remove blockers.
                    Consider adjusting team capacity or breaking down large items.
                  </div>
                </div>
              </div>
            </AlertDescription>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className={`h-6 w-6 p-0 ml-2 ${severityColor.text} hover:${severityColor.text} hover:bg-red-100 dark:hover:bg-red-900`}
          onClick={() => setIsDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </Alert>
  )
}
