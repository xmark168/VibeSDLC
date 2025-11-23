import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { format } from "date-fns"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface ExecutionTrendsChartProps {
  data: Array<{
    timestamp: string
    total: number
    successful: number
    failed: number
    success_rate: number
  }>
  title?: string
  description?: string
}

export function ExecutionTrendsChart({
  data,
  title = "Execution Trends",
  description = "Execution volume and success rate over time",
}: ExecutionTrendsChartProps) {
  const formattedData = data.map((d) => ({
    ...d,
    time: format(new Date(d.timestamp), "HH:mm"),
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="successful" fill="#10b981" name="Successful" />
            <Bar yAxisId="left" dataKey="failed" fill="#ef4444" name="Failed" />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="success_rate"
              stroke="#3b82f6"
              name="Success Rate (%)"
              strokeWidth={2}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
