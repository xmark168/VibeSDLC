import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, Search, Calendar, TrendingUp, AlertCircle } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'

interface BacklogItem {
  id: string
  type: 'Epic' | 'User Story' | 'Task' | 'Sub-task'
  title: string
  rank?: number
  wsjf_score?: number
  story_point?: number | null
  dependencies?: string[]
}

interface Sprint {
  sprint_id: string
  sprint_number: number
  sprint_goal: string
  start_date: string
  end_date: string
  velocity_plan: number
  velocity_actual?: number
  assigned_items: string[]
  status: 'Planned' | 'Active' | 'Completed'
}

interface SprintPlanMetadata {
  product_name: string
  version?: string
  created_at?: string
  sprint_duration_weeks: number
  sprint_capacity_story_points: number
  total_sprints: number
  total_items_assigned: number
  total_story_points: number
  total_unassigned_items?: number
  readiness_score: number
  status?: string
}

interface SprintPlanPreviewProps {
  sprintPlan: {
    metadata: SprintPlanMetadata
    prioritized_backlog: BacklogItem[]
    wsjf_calculations?: Record<string, any>
    sprints: Sprint[]
    unassigned_items?: BacklogItem[]
  }
}

export function SprintPlanPreview({ sprintPlan }: SprintPlanPreviewProps) {
  const [expandedSprints, setExpandedSprints] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [sprintFilter, setSprintFilter] = useState<string>('all')
  const [showBacklogTable, setShowBacklogTable] = useState(false)

  if (!sprintPlan || !sprintPlan.metadata || !sprintPlan.sprints) {
    return <div className="text-center text-muted-foreground">Không có dữ liệu sprint plan</div>
  }

  const { metadata, sprints, prioritized_backlog, unassigned_items } = sprintPlan

  // Build item map for quick lookup
  const itemsMap = useMemo(() => {
    const map = new Map<string, BacklogItem>()
    prioritized_backlog?.forEach(item => map.set(item.id, item))
    return map
  }, [prioritized_backlog])

  // Filter sprints based on search
  const filteredSprints = useMemo(() => {
    return sprints.filter(sprint => {
      const matchesSearch = searchQuery === '' ||
        sprint.sprint_goal.toLowerCase().includes(searchQuery.toLowerCase()) ||
        sprint.sprint_id.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesSprint = sprintFilter === 'all' || sprint.sprint_id === sprintFilter

      return matchesSearch && matchesSprint
    })
  }, [sprints, searchQuery, sprintFilter])

  const toggleSprint = (sprintId: string) => {
    setExpandedSprints(prev => {
      const next = new Set(prev)
      if (next.has(sprintId)) {
        next.delete(sprintId)
      } else {
        next.add(sprintId)
      }
      return next
    })
  }

  const getCapacityColor = (velocity: number, capacity: number): string => {
    const utilization = (velocity / capacity) * 100
    if (utilization > 100) return 'text-red-600 dark:text-red-400'
    if (utilization < 70) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-green-600 dark:text-green-400'
  }

  const getCapacityIcon = (velocity: number, capacity: number): string => {
    const utilization = (velocity / capacity) * 100
    if (utilization > 100) return '🔴'
    if (utilization < 70) return '🟡'
    return '🟢'
  }

  const getUtilizationPercent = (velocity: number, capacity: number): number => {
    return Math.min((velocity / capacity) * 100, 100)
  }

  const renderSprintCard = (sprint: Sprint) => {
    const isExpanded = expandedSprints.has(sprint.sprint_id)
    const capacity = metadata.sprint_capacity_story_points
    const utilization = (sprint.velocity_plan / capacity) * 100
    const capacityIcon = getCapacityIcon(sprint.velocity_plan, capacity)
    const capacityColor = getCapacityColor(sprint.velocity_plan, capacity)

    // Get assigned items details
    const assignedItems = sprint.assigned_items
      .map(itemId => itemsMap.get(itemId))
      .filter(Boolean) as BacklogItem[]

    return (
      <Card key={sprint.sprint_id} className="mb-3">
        <CardHeader
          className="cursor-pointer hover:bg-accent/50 transition-colors"
          onClick={() => toggleSprint(sprint.sprint_id)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              {isExpanded ? (
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-5 h-5 text-muted-foreground" />
              )}
              <div className="flex-1">
                <div className="flex flex-col">
                  <CardTitle className="text-base">
                    Sprint {sprint.sprint_number}
                  </CardTitle>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">
                      {sprint.start_date} → {sprint.end_date}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className={`flex items-center gap-2 font-medium ${capacityColor}`}>
                <span>{capacityIcon}</span>
                <span>{sprint.velocity_plan}/{capacity} pts</span>
                <span className="text-xs">({utilization.toFixed(0)}%)</span>
              </div>
            </div>
          </div>
        </CardHeader>

        {isExpanded && (
          <CardContent className="pt-0">
            <div className="space-y-3">
              {/* Capacity Progress Bar */}
              <div>
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>Capacity Utilization</span>
                  <span>{sprint.velocity_plan} / {capacity} story points</span>
                </div>
                <Progress
                  value={getUtilizationPercent(sprint.velocity_plan, capacity)}
                  className="h-2"
                />
              </div>

              {/* Assigned Items */}
              <div>
                <h5 className="text-sm font-semibold mb-2">
                  Assigned Items ({assignedItems.length})
                </h5>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {assignedItems.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic">
                      Chưa có items được assign
                    </p>
                  ) : (
                    assignedItems.map(item => (
                      <div
                        key={item.id}
                        className="flex items-center gap-2 p-2 bg-muted/50 rounded text-xs"
                      >
                        <Badge variant="outline" className="text-xs font-mono">
                          {item.id}
                        </Badge>
                        <span className="flex-1 truncate">{item.title}</span>
                        {item.story_point && (
                          <Badge variant="secondary" className="text-xs">
                            {item.story_point} SP
                          </Badge>
                        )}
                        {item.rank && (
                          <span className="text-muted-foreground">
                            Rank #{item.rank}
                          </span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Metadata Summary */}
      <div className="p-4 bg-muted rounded-lg">
        <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Tóm tắt Sprint Plan
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-muted-foreground">Sản phẩm:</span>
            <span className="ml-2 font-medium">{metadata.product_name}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Version:</span>
            <span className="ml-2 font-medium">{metadata.version || 'v1.0'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Readiness Score:</span>
            <span className="ml-2 font-medium">{(metadata.readiness_score * 100).toFixed(0)}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Total Sprints:</span>
            <span className="ml-2 font-medium">{metadata.total_sprints}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Items Assigned:</span>
            <span className="ml-2 font-medium">{metadata.total_items_assigned}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Story Points:</span>
            <span className="ml-2 font-medium">{metadata.total_story_points}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Sprint Duration:</span>
            <span className="ml-2 font-medium">{metadata.sprint_duration_weeks} weeks</span>
          </div>
          <div>
            <span className="text-muted-foreground">Sprint Capacity:</span>
            <span className="ml-2 font-medium">{metadata.sprint_capacity_story_points} pts</span>
          </div>
          {metadata.total_unassigned_items !== undefined && metadata.total_unassigned_items > 0 && (
            <div>
              <span className="text-muted-foreground">Unassigned:</span>
              <span className="ml-2 font-medium text-yellow-600 dark:text-yellow-400">
                {metadata.total_unassigned_items} items
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Nhập tên"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={sprintFilter} onValueChange={setSprintFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Chọn sprint" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tất cả sprints</SelectItem>
            {sprints.map(s => (
              <SelectItem key={s.sprint_id} value={s.sprint_id}>
                Sprint {s.sprint_number}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Sprints List */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold">Sprints Breakdown</h4>
        <div className="max-h-[500px] overflow-y-auto space-y-2">
          {filteredSprints.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">
              Không tìm thấy sprint phù hợp
            </div>
          ) : (
            filteredSprints.map(sprint => renderSprintCard(sprint))
          )}
        </div>
      </div>

      {/* Unassigned Items Warning */}
      {unassigned_items && unassigned_items.length > 0 && (
        <Card className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
              <AlertCircle className="w-4 h-4" />
              Unassigned Items ({unassigned_items.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-2">
              Các items sau chưa được assign vào sprint (có thể do dependencies hoặc capacity):
            </p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {unassigned_items.slice(0, 5).map(item => (
                <div key={item.id} className="flex items-center gap-2 text-xs">
                  <Badge variant="outline" className="text-xs font-mono">
                    {item.id}
                  </Badge>
                  <span className="flex-1 truncate">{item.title}</span>
                  {item.rank && (
                    <span className="text-muted-foreground">Rank #{item.rank}</span>
                  )}
                </div>
              ))}
              {unassigned_items.length > 5 && (
                <p className="text-xs text-muted-foreground italic">
                  ... và {unassigned_items.length - 5} items khác
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prioritized Backlog Toggle */}
      <div className="border-t pt-3">
        <button
          onClick={() => setShowBacklogTable(!showBacklogTable)}
          className="text-sm font-medium text-primary hover:underline flex items-center gap-2"
        >
          {showBacklogTable ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          Xem Prioritized Backlog với WSJF Scores ({prioritized_backlog?.length || 0} items)
        </button>

        {showBacklogTable && prioritized_backlog && prioritized_backlog.length > 0 && (
          <div className="mt-3 border rounded-md max-h-80 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Rank</TableHead>
                  <TableHead className="w-28">ID</TableHead>
                  <TableHead className="w-28">Type</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead className="w-24 text-right">WSJF</TableHead>
                  <TableHead className="w-24 text-right">Story Points</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {prioritized_backlog.slice(0, 20).map(item => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">#{item.rank || 'N/A'}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-mono">
                        {item.id}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {item.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="truncate max-w-md">{item.title}</TableCell>
                    <TableCell className="text-right font-medium">
                      {item.wsjf_score?.toFixed(2) || 'N/A'}
                    </TableCell>
                    <TableCell className="text-right">
                      {item.story_point || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {prioritized_backlog.length > 20 && (
              <div className="text-xs text-center text-muted-foreground py-2 border-t">
                Hiển thị 20 / {prioritized_backlog.length} items
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
