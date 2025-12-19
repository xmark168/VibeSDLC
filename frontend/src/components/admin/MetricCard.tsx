import { Minus, TrendingDown, TrendingUp } from "lucide-react"
import { Line, LineChart, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface MetricCardProps {
  title: string
  value: string | number
  change?: number // Percentage change
  trend?: Array<{ value: number }> // Sparkline data
  icon?: React.ReactNode
  subtitle?: string
}

export function MetricCard({
  title,
  value,
  change,
  trend,
  icon,
  subtitle,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (change === undefined || change === 0) {
      return <Minus className="h-4 w-4 text-gray-400" />
    }
    return change > 0 ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-600" />
    )
  }

  const getTrendColor = () => {
    if (change === undefined || change === 0) return "text-gray-600"
    return change > 0 ? "text-green-600" : "text-red-600"
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
        <div className="flex items-center justify-between mt-2">
          {change !== undefined && (
            <div
              className={cn(
                "flex items-center text-xs font-medium",
                getTrendColor(),
              )}
            >
              {getTrendIcon()}
              <span className="ml-1">{Math.abs(change).toFixed(1)}%</span>
            </div>
          )}
          {trend && trend.length > 0 && (
            <div className="h-8 flex-1 ml-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend}>
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={
                      change && change > 0
                        ? "#16a34a"
                        : change && change < 0
                          ? "#dc2626"
                          : "#6b7280"
                    }
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
