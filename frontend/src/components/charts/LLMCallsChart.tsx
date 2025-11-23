import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts"
import { format } from "date-fns"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface LLMCallsChartProps {
  data: Array<{
    timestamp?: string
    pool_name?: string
    llm_calls: number
    tokens?: number
    avg_tokens_per_call?: number
  }>
  title?: string
  description?: string
  chartType?: "bar" | "line"
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

export function LLMCallsChart({
  data,
  title = "LLM API Calls",
  description = "LLM API usage and token consumption",
  chartType = "bar",
}: LLMCallsChartProps) {
  const hasTimestamp = data.length > 0 && "timestamp" in data[0]

  const formattedData = hasTimestamp
    ? data.map((d) => ({
        ...d,
        time: d.timestamp ? format(new Date(d.timestamp), "HH:mm") : "",
      }))
    : data

  const totalCalls = data.reduce((sum, d) => sum + d.llm_calls, 0)
  const totalTokens = data.reduce((sum, d) => sum + (d.tokens || 0), 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Calls:</span>{" "}
            <span className="font-semibold">{totalCalls.toLocaleString()}</span>
          </div>
          {totalTokens > 0 && (
            <div>
              <span className="text-muted-foreground">Total Tokens:</span>{" "}
              <span className="font-semibold">{totalTokens.toLocaleString()}</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          {chartType === "bar" ? (
            <BarChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={hasTimestamp ? "time" : "pool_name"} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="llm_calls" fill="#3b82f6" name="LLM Calls">
                {!hasTimestamp &&
                  formattedData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
              </Bar>
            </BarChart>
          ) : (
            <LineChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="llm_calls"
                stroke="#3b82f6"
                strokeWidth={2}
                name="LLM Calls"
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
