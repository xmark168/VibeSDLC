import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { format } from "date-fns"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface SuccessRateChartProps {
  data: Array<{
    timestamp: string
    success_rate: number
    successful: number
    failed: number
  }>
  title?: string
  description?: string
  showArea?: boolean
}

export function SuccessRateChart({
  data,
  title = "Success Rate Trend",
  description = "Agent execution success rate over time",
  showArea = false,
}: SuccessRateChartProps) {
  const formattedData = data.map((d) => ({
    ...d,
    time: format(new Date(d.timestamp), "HH:mm"),
  }))

  const avgSuccessRate =
    data.reduce((sum, d) => sum + d.success_rate, 0) / (data.length || 1)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        <div className="text-sm">
          <span className="text-muted-foreground">Average:</span>{" "}
          <span
            className={`font-semibold ${
              avgSuccessRate >= 95 ? "text-green-600" : avgSuccessRate >= 80 ? "text-yellow-600" : "text-red-600"
            }`}
          >
            {avgSuccessRate.toFixed(1)}%
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          {showArea ? (
            <AreaChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              <Legend />
              <Area
                type="monotone"
                dataKey="success_rate"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.6}
                name="Success Rate (%)"
              />
            </AreaChart>
          ) : (
            <LineChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              <Legend />
              <Line
                type="monotone"
                dataKey="success_rate"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 4 }}
                name="Success Rate (%)"
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
