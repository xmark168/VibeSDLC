import { X, Eye, Zap, User } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"

export type KanbanCardData = {
  id: string
  content: string
  columnId: string
  agentName?: string
  agentAvatar?: string
  taskId?: string
  result?: string
  subtasks?: string[]
  branch?: string
  // Backlog item fields
  type?: string
  description?: string
  status?: string
  story_point?: number
  estimate_value?: number
  rank?: number
  assignee_id?: string
  reviewer_id?: string
  // TraDS ============= Kanban Hierarchy: Parent/children relationships
  parent?: KanbanCardData
  children?: KanbanCardData[]
}

interface KanbanCardProps {
  card: KanbanCardData
  isDragging?: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onClick: () => void
  onDelete: () => void
  onDownloadResult: () => void
}

export function KanbanCard({
  card,
  isDragging,
  onDragStart,
  onDragEnd,
  onClick,
  onDelete,
  onDownloadResult,
}: KanbanCardProps) {
  // Get type badge color
  const getTypeBadgeColor = (type?: string) => {
    switch (type) {
      case "Epic":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400"
      case "User Story":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400"
      case "Task":
        return "bg-green-500/10 text-green-600 dark:text-green-400"
      case "Sub-task":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400"
    }
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={`bg-card rounded-lg border border-border p-3 group relative hover:shadow-md transition-all cursor-pointer ${isDragging ? "opacity-50" : ""
        }`}
    >
      {/* Action Buttons */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        {card.result && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDownloadResult()
            }}
            className="p-1.5 rounded hover:bg-muted bg-background/80"
            title="Download result"
          >
            <Eye className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          className="p-1.5 rounded hover:bg-muted bg-background/80"
        >
          <X className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
        </button>
      </div>

      <div className="space-y-2">
        {/* Header: Type Badge and Story Points */}
        <div className="flex items-center justify-between gap-2">
          {card.type && (
            <Badge variant="outline" className={`text-xs ${getTypeBadgeColor(card.type)}`}>
              {card.type}
            </Badge>
          )}
          {card.story_point !== undefined && card.story_point !== null && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Zap className="w-3 h-3" />
              <span>{card.story_point} SP</span>
            </div>
          )}
        </div>

        {/* Task Title */}
        <h4 className="text-sm font-medium text-foreground line-clamp-2 pr-16">{card.content}</h4>

        {/* Description (if available) */}
        {card.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">{card.description}</p>
        )}

        {/* Footer: Task ID, Priority, Assignee */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-2">
            {card.taskId && (
              <span className="text-xs text-muted-foreground font-mono">#{card.taskId.slice(0, 8)}</span>
            )}
            {card.rank !== undefined && card.rank !== null && (
              <Badge
                variant="outline"
                className={`text-xs ${card.rank <= 3
                    ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
                    : card.rank <= 7
                      ? "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
                      : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                  }`}
              >
                #{card.rank}
              </Badge>
            )}
          </div>
          {card.assignee_id && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <User className="w-3 h-3" />
              <span className="truncate max-w-[60px]">{card.assignee_id.slice(0, 8)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
