import { useState, useEffect } from "react"
import { TrendingUp, Calendar } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"

interface CFDData {
  date: string
  Todo: number
  InProgress: number
  Review: number
  Done: number
}

interface CumulativeFlowDiagramProps {
  projectId?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CumulativeFlowDiagram({
  projectId,
  open,
  onOpenChange,
}: CumulativeFlowDiagramProps) {
  const [timeRange, setTimeRange] = useState("30")
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CFDData[]>([])

  useEffect(() => {
    if (open && projectId) {
      loadCFDData()
    }
  }, [open, projectId, timeRange])

  const loadCFDData = async () => {
    setLoading(true)
    try {
      // TODO: Replace with actual API call
      // const response = await backlogItemsApi.getCFDData(projectId, parseInt(timeRange))
      // setData(response)

      // Mock data for demonstration
      const mockData: CFDData[] = []
      const days = parseInt(timeRange)
      const today = new Date()

      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today)
        date.setDate(date.getDate() - i)

        mockData.push({
          date: date.toISOString().split("T")[0],
          Todo: Math.floor(Math.random() * 10) + 5,
          InProgress: Math.floor(Math.random() * 5) + 2,
          Review: Math.floor(Math.random() * 3) + 1,
          Done: Math.floor(Math.random() * 20) + days - i,
        })
      }

      setData(mockData)
    } catch (error) {
      console.error("Failed to load CFD data:", error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { key: "Done", label: "Done", color: "#10b981" },
    { key: "Review", label: "Review", color: "#f97316" },
    { key: "InProgress", label: "In Progress", color: "#3b82f6" },
    { key: "Todo", label: "To Do", color: "#8b5cf6" },
  ]

  // Calculate cumulative values for stacked area chart
  const cumulativeData = data.map((day) => {
    let cumulative = 0
    const result: any = { date: day.date }

    columns.forEach((col) => {
      cumulative += day[col.key as keyof CFDData] as number
      result[col.key] = cumulative
    })

    return result
  })

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  }

  // Calculate current WIP (items not in Done)
  const latestData = data[data.length - 1]
  const currentWIP = latestData
    ? (latestData.Todo || 0) +
      (latestData.InProgress || 0) +
      (latestData.Review || 0)
    : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Cumulative Flow Diagram
          </DialogTitle>
          <DialogDescription>
            Visualize work items flowing through your workflow over time.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Time Range:</span>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7 days</SelectItem>
                <SelectItem value="14">14 days</SelectItem>
                <SelectItem value="30">30 days</SelectItem>
                <SelectItem value="60">60 days</SelectItem>
                <SelectItem value="90">90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Current WIP:</span>
            <Badge variant="outline" className="font-mono">
              {currentWIP}
            </Badge>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-sm text-muted-foreground">Loading chart data...</div>
          </div>
        ) : data.length === 0 ? (
          <Alert>
            <AlertDescription>
              No data available for the selected time range. Data collection may not be enabled yet.
            </AlertDescription>
          </Alert>
        ) : (
          <>
            {/* SVG-based Stacked Area Chart */}
            <div className="relative w-full h-96 bg-muted/20 rounded-lg border p-4">
              <svg width="100%" height="100%" viewBox="0 0 800 300" preserveAspectRatio="none">
                <defs>
                  {columns.map((col) => (
                    <linearGradient key={col.key} id={`gradient-${col.key}`} x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor={col.color} stopOpacity="0.8" />
                      <stop offset="100%" stopColor={col.color} stopOpacity="0.3" />
                    </linearGradient>
                  ))}
                </defs>

                {/* Grid lines */}
                {[0, 1, 2, 3, 4].map((i) => (
                  <line
                    key={i}
                    x1="0"
                    y1={i * 75}
                    x2="800"
                    y2={i * 75}
                    stroke="currentColor"
                    strokeOpacity="0.1"
                    strokeWidth="1"
                  />
                ))}

                {/* Render stacked areas from bottom to top */}
                {columns.map((col, colIndex) => {
                  const points = cumulativeData
                    .map((d, i) => {
                      const x = (i / (cumulativeData.length - 1)) * 800
                      const maxValue = Math.max(...cumulativeData.map((d) => d.Done))
                      const y = 300 - (d[col.key] / maxValue) * 300
                      return `${x},${y}`
                    })
                    .join(" ")

                  // Create polygon for filled area
                  const polygonPoints = [
                    ...cumulativeData.map((d, i) => {
                      const x = (i / (cumulativeData.length - 1)) * 800
                      const maxValue = Math.max(...cumulativeData.map((d) => d.Done))
                      const y = 300 - (d[col.key] / maxValue) * 300
                      return `${x},${y}`
                    }),
                    // Add bottom edge
                    ...(colIndex > 0
                      ? cumulativeData
                          .slice()
                          .reverse()
                          .map((d, i) => {
                            const x = 800 - (i / (cumulativeData.length - 1)) * 800
                            const maxValue = Math.max(...cumulativeData.map((d) => d.Done))
                            const prevCol = columns[colIndex - 1]
                            const y = 300 - (d[prevCol.key] / maxValue) * 300
                            return `${x},${y}`
                          })
                      : [`800,300`, `0,300`]),
                  ].join(" ")

                  return (
                    <g key={col.key}>
                      <polygon
                        points={polygonPoints}
                        fill={`url(#gradient-${col.key})`}
                        stroke={col.color}
                        strokeWidth="2"
                      />
                    </g>
                  )
                })}
              </svg>

              {/* X-axis labels */}
              <div className="absolute bottom-1 left-4 right-4 flex justify-between text-xs text-muted-foreground">
                {[0, Math.floor(data.length / 2), data.length - 1].map((i) => (
                  <span key={i}>{data[i] ? formatDate(data[i].date) : ""}</span>
                ))}
              </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center justify-center gap-4 mt-4">
              {columns.map((col) => (
                <div key={col.key} className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: col.color }}
                  />
                  <span className="text-sm text-foreground">{col.label}</span>
                </div>
              ))}
            </div>

            {/* Insights */}
            <Alert className="mt-4">
              <AlertDescription className="text-sm">
                <strong>How to read this chart:</strong> The height of each colored band represents the number of
                items in that status. Increasing band height indicates accumulation (bottleneck). The total height
                shows cumulative throughput.
              </AlertDescription>
            </Alert>
          </>
        )}

        <div className="flex justify-end mt-4">
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
