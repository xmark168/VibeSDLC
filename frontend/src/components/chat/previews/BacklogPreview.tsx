import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, Search, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

interface BacklogItem {
  id: string
  type: 'Epic' | 'User Story' | 'Task' | 'Sub-task'
  parent_id: string | null
  title: string
  description?: string
  rank?: number | null
  status?: string
  story_point?: number | null
  estimate_value?: number | null
  acceptance_criteria?: string[]
  dependencies?: string[]
  labels?: string[]
}

interface BacklogMetadata {
  product_name?: string
  version?: string
  total_items: number
  total_epics: number
  total_user_stories: number
  total_tasks: number
  total_subtasks: number
  total_story_points: number
  total_estimate_hours: number
}

interface BacklogPreviewProps {
  backlog: {
    metadata: BacklogMetadata
    items: BacklogItem[]
  }
}

export function BacklogPreview({ backlog }: BacklogPreviewProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')

  if (!backlog || !backlog.items) return null

  const { metadata, items } = backlog

  // Filter items based on search and type filter
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchesSearch = searchQuery === '' ||
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesType = typeFilter === 'all' || item.type === typeFilter

      return matchesSearch && matchesType
    })
  }, [items, searchQuery, typeFilter])

  // Build hierarchical structure
  const itemsMap = useMemo(() => {
    const map = new Map<string, BacklogItem>()
    items.forEach(item => map.set(item.id, item))
    return map
  }, [items])

  const rootItems = useMemo(() => {
    // If filtering by specific type OR searching, show all filtered items as root (flatten view)
    // This allows viewing User Stories, Tasks, etc. even if they have parents
    if (typeFilter !== 'all' || searchQuery !== '') {
      return filteredItems
    }
    // Otherwise, show only true root items (hierarchical view)
    return filteredItems.filter(item => !item.parent_id)
  }, [filteredItems, typeFilter, searchQuery])

  const getChildren = (parentId: string): BacklogItem[] => {
    // Don't show children when filtering by specific type OR searching (flatten view)
    if (typeFilter !== 'all' || searchQuery !== '') {
      return []
    }
    return filteredItems.filter(item => item.parent_id === parentId)
  }

  const toggleExpand = (itemId: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(itemId)) {
        next.delete(itemId)
      } else {
        next.add(itemId)
      }
      return next
    })
  }

  const getTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'Epic':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
      case 'User Story':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
      case 'Task':
        return 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
      case 'Sub-task':
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const renderItem = (item: BacklogItem, depth: number = 0) => {
    const children = getChildren(item.id)
    const hasChildren = children.length > 0
    const isExpanded = expandedItems.has(item.id)
    const paddingLeft = `${depth * 1.5}rem`

    return (
      <div key={item.id}>
        <Card
          className="mb-2 hover:bg-accent/50 transition-colors cursor-pointer"
          style={{ marginLeft: paddingLeft }}
        >
          <CardContent className="p-3">
            <div className="flex items-start gap-2">
              {hasChildren && (
                <button
                  onClick={() => toggleExpand(item.id)}
                  className="mt-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded p-0.5"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>
              )}
              {!hasChildren && <div className="w-5" />}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <Badge variant="outline" className="text-xs font-mono">
                    {item.id}
                  </Badge>
                  <Badge className={`text-xs ${getTypeBadgeColor(item.type)}`}>
                    {item.type}
                  </Badge>
                  {item.story_point && (
                    <Badge variant="secondary" className="text-xs">
                      {item.story_point} SP
                    </Badge>
                  )}
                  {item.estimate_value && (
                    <Badge variant="secondary" className="text-xs">
                      {item.estimate_value}h
                    </Badge>
                  )}
                </div>

                <h5 className="text-sm font-medium text-foreground mb-1">
                  {item.title}
                </h5>

                {item.parent_id && (
                  <p className="text-xs text-muted-foreground">
                    Parent: {item.parent_id}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {hasChildren && isExpanded && (
          <div>
            {children.map(child => renderItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Metadata Summary */}
      <div className="p-4 bg-muted rounded-lg">
        <h4 className="text-sm font-semibold text-foreground mb-2">
          📊 Tóm tắt Backlog
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-muted-foreground">Sản phẩm:</span>
            <span className="ml-2 font-medium">{metadata.product_name || 'N/A'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Version:</span>
            <span className="ml-2 font-medium">{metadata.version || 'N/A'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Tổng items:</span>
            <span className="ml-2 font-medium">{metadata.total_items}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Story Points:</span>
            <span className="ml-2 font-medium">{metadata.total_story_points}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Epics:</span>
            <span className="ml-2 font-medium">{metadata.total_epics}</span>
          </div>
          <div>
            <span className="text-muted-foreground">User Stories:</span>
            <span className="ml-2 font-medium">{metadata.total_user_stories}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Tasks:</span>
            <span className="ml-2 font-medium">{metadata.total_tasks}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Sub-tasks:</span>
            <span className="ml-2 font-medium">{metadata.total_subtasks}</span>
          </div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Tìm kiếm theo tên hoặc ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Lọc theo loại" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tất cả</SelectItem>
            <SelectItem value="Epic">Epic</SelectItem>
            <SelectItem value="User Story">User Story</SelectItem>
            <SelectItem value="Task">Task</SelectItem>
            <SelectItem value="Sub-task">Sub-task</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Hierarchical Tree View */}
      <div className="space-y-2">
        {rootItems.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-8">
            Không tìm thấy items phù hợp
          </div>
        ) : (
          rootItems.map(item => renderItem(item, 0))
        )}
      </div>

      {/* Item Count */}
      <div className="text-xs text-muted-foreground text-center">
        Hiển thị {filteredItems.length} / {items.length} items
      </div>
    </div>
  )
}
