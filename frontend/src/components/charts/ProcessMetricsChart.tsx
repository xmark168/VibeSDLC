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
import { Progress } from "@/components/ui/progress"

interface ProcessMetricsChartProps {
  summary: {
    total_processes: number
    total_capacity: number
    used_capacity: number
    avg_utilization: number
  }
  processes: Array<{
    process_id: string
    pool_name: string
    agent_count: number
    max_agents: number
    utilization: number
  }>
  title?: string
  description?: string
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

export function ProcessMetricsChart({
  summary,
  processes,
  title = "Worker Process Distribution",
  description = "Agent distribution across multiprocessing worker processes",
}: ProcessMetricsChartProps) {
  const chartData = processes.map((p) => ({
    name: `${p.pool_name}\n(${p.process_id.slice(0, 8)})`,
    agents: p.agent_count,
    capacity: p.max_agents,
    utilization: p.utilization,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Processes:</span>{" "}
            <span className="font-semibold">{summary.total_processes}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Capacity:</span>{" "}
            <span className="font-semibold">
              {summary.used_capacity}/{summary.total_capacity}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Avg Utilization:</span>{" "}
            <span className="font-semibold">{summary.avg_utilization.toFixed(1)}%</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={150} />
            <Tooltip />
            <Legend />
            <Bar dataKey="agents" fill="#3b82f6" name="Agents">
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.utilization > 80
                      ? "#ef4444"
                      : entry.utilization > 50
                        ? "#f59e0b"
                        : "#10b981"
                  }
                />
              ))}
            </Bar>
            <Bar dataKey="capacity" fill="#e5e7eb" name="Max Capacity" />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4">
          <div className="text-sm font-medium mb-2">Overall Utilization</div>
          <Progress value={summary.avg_utilization} className="h-2" />
        </div>
      </CardContent>
    </Card>
  )
}
