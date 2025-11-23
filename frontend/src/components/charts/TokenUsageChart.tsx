import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface TokenUsageChartProps {
  data: Array<{
    pool_name: string
    total_tokens: number
    total_llm_calls: number
    estimated_cost_usd: number
  }>
  title?: string
  description?: string
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

export function TokenUsageChart({
  data,
  title = "Token Usage by Pool",
  description = "Token consumption and costs across agent pools",
}: TokenUsageChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="pool_name" />
            <YAxis />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === "estimated_cost_usd") {
                  return [`$${value.toFixed(4)}`, "Est. Cost"]
                }
                return [value.toLocaleString(), name]
              }}
            />
            <Legend />
            <Bar dataKey="total_tokens" fill="#3b82f6" name="Total Tokens">
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 text-sm text-muted-foreground">
          Total Cost: ${data.reduce((sum, d) => sum + d.estimated_cost_usd, 0).toFixed(4)}
        </div>
      </CardContent>
    </Card>
  )
}
