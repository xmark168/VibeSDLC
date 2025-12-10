import { X, Eye, Zap, User, MoreVertical, Copy, Edit, Trash2, MoveRight, Link2, Ban, Loader2, Clock } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useState, memo } from "react"

export type KanbanCardData = {
  id: string
  content: string
  columnId: string
  agentName?: string
  agentAvatar?: string
  taskId?: string
  story_code?: string  // e.g., "EPIC-001-US-001"
  result?: string
  subtasks?: string[]
  branch?: string
  // Backlog item fields
  type?: string
  description?: string
  status?: string
  story_point?: number
  priority?: number
  rank?: number
  assignee_id?: string
  reviewer_id?: string
  epic_id?: string
  epic_code?: string
  epic_title?: string
  epic_description?: string
  epic_domain?: string
  acceptance_criteria?: string[]
  requirements?: string[]
  dependencies?: string[]  // List of story IDs that must be completed before this story
  // Flow metrics
  created_at?: string
  updated_at?: string
  age_hours?: number  // Age in current status (hours)
  // Agent state
  agent_state?: 'pending' | 'processing' | 'canceled' | 'finished' | null
  running_port?: number | null
  running_pid?: number | null
  worktree_path?: string | null
  worktree_path_display?: string | null
  branch_name?: string | null
  pr_url?: string | null
  merge_status?: string | null  // "not_merged", "merged", "conflict"
  started_at?: string | null
  // TraDS ============= Kanban Hierarchy: Parent/children relationships
  parent?: KanbanCardData
  children?: KanbanCardData[]
  // Blocked state - dependencies not completed
  isBlocked?: boolean
  blockedByCount?: number
}

interface KanbanCardProps {
  card: KanbanCardData
  isDragging?: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onClick: () => void
  onDelete: () => void
  onDownloadResult: () => void
  onDuplicate?: () => void
  onMove?: (targetColumn: string) => void
  onEdit?: () => void
}

function KanbanCardComponent({
  card,
  isDragging,
  onDragStart,
  onDragEnd,
  onClick,
  onDelete,
  onDownloadResult,
  onDuplicate,
  onMove,
  onEdit,
}: KanbanCardProps) {
  const [showQuickActions, setShowQuickActions] = useState(false)
  
  // Check if card can be dragged based on agent_state
  const canDrag = !card.agent_state || card.agent_state === 'finished' || card.agent_state === 'canceled'
  const isAgentRunning = card.agent_state === 'pending' || card.agent_state === 'processing'

  // Get type badge color - Modern & Minimal: More subtle colors
  // Lean Kanban: Only UserStory and EnablerStory on board
  const getTypeBadgeColor = (type?: string) => {
    const normalizedType = type?.toUpperCase()
    switch (normalizedType) {
      case "USERSTORY":
      case "USER_STORY":
        return "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 border-blue-200/50 dark:border-blue-800/50"
      case "ENABLERSTORY":
      case "ENABLER_STORY":
        return "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200/50 dark:border-emerald-800/50"
      default:
        return "bg-slate-50 dark:bg-slate-900/30 text-slate-700 dark:text-slate-300 border-slate-200/50 dark:border-slate-800/50"
    }
  }

  // Format type name for display (UserStory/USER_STORY -> User Story)
  const formatTypeName = (type?: string) => {
    if (!type) return ""
    const normalizedType = type.toUpperCase()
    switch (normalizedType) {
      case "USERSTORY":
      case "USER_STORY":
        return "User Story"
      case "ENABLERSTORY":
      case "ENABLER_STORY":
        return "Enabler Story"
      default:
        return type
    }
  }

  // Format age display
  const formatAge = (hours?: number) => {
    if (!hours) return null
    if (hours < 24) return `${Math.round(hours)}h`
    const days = Math.floor(hours / 24)
    return `${days}d`
  }

  // Get age badge color based on age - Modern & Minimal: Softer warning colors
  const getAgeBadgeColor = (hours?: number) => {
    if (!hours) return ""
    if (hours >= 120) { // 5+ days
      return "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200/50 dark:border-red-800/50"
    } else if (hours >= 72) { // 3-5 days
      return "bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-300 border-orange-200/50 dark:border-orange-800/50"
    } else if (hours >= 48) { // 2-3 days
      return "bg-yellow-50 dark:bg-yellow-950/30 text-yellow-700 dark:text-yellow-300 border-yellow-200/50 dark:border-yellow-800/50"
    } else {
      return "bg-slate-50 dark:bg-slate-900/30 text-slate-600 dark:text-slate-400 border-slate-200/50 dark:border-slate-800/50"
    }
  }

  return (
    <div
      draggable={canDrag}
      onDragStart={canDrag ? onDragStart : undefined}
      onDragEnd={canDrag ? onDragEnd : undefined}
      onClick={onClick}
      className={`
        rounded-xl border
        p-4 group relative
        hover:shadow-sm
        transition-all duration-200
        ${isDragging ? "opacity-50 scale-95" : ""}
        ${!canDrag ? "cursor-not-allowed" : "cursor-grab"}
        ${isAgentRunning ? "ring-2 ring-blue-400/50 dark:ring-blue-500/40" : ""}
        ${card.isBlocked 
          ? "bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-900/60 hover:border-red-300 dark:hover:border-red-800" 
          : "bg-card border-border/50 hover:border-border"
        }
      `}
      title={!canDrag ? `Cannot drag: Agent is ${card.agent_state}` : undefined}
    >
      {/* Action Buttons - Quick Actions Menu */}
      <div className="absolute top-3 right-3 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        {/* Quick Actions Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              onClick={(e) => e.stopPropagation()}
              className="p-1.5 rounded-lg hover:bg-muted/80 bg-background/90 backdrop-blur-sm shadow-sm"
              title="Quick actions"
            >
              <MoreVertical className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground transition-colors" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {onEdit && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit()
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                <span>Edit</span>
                <span className="ml-auto text-xs text-muted-foreground">E</span>
              </DropdownMenuItem>
            )}
            {onDuplicate && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  onDuplicate()
                }}
              >
                <Copy className="w-4 h-4 mr-2" />
                <span>Duplicate</span>
                <span className="ml-auto text-xs text-muted-foreground">D</span>
              </DropdownMenuItem>
            )}
            {onMove && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <MoveRight className="w-4 h-4 mr-2" />
                  <span>Move to</span>
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {["todo", "inprogress", "review", "done"].map((col) => {
                    const colName = col === "inprogress" ? "InProgress" : col.charAt(0).toUpperCase() + col.slice(1)
                    return (
                      <DropdownMenuItem
                        key={col}
                        onClick={(e) => {
                          e.stopPropagation()
                          onMove(col)
                        }}
                        disabled={card.columnId === col}
                      >
                        {colName}
                      </DropdownMenuItem>
                    )
                  })}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}
            {card.result && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  onDownloadResult()
                }}
              >
                <Eye className="w-4 h-4 mr-2" />
                <span>Download Result</span>
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              <span>Delete</span>
              <span className="ml-auto text-xs">⌫</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="space-y-3">
        {/* Header: Type Badge, Agent State Badge, Blocked Badge and Age */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            {card.type && (
              <Badge variant="outline" className={`text-xs font-medium ${getTypeBadgeColor(card.type)}`}>
                {formatTypeName(card.type)}
              </Badge>
            )}
            {/* Agent State Badge - Show when pending or processing */}
            {card.agent_state === 'pending' && (
              <Badge variant="outline" className="text-xs font-medium gap-1 bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700 animate-pulse">
                <Clock className="w-3 h-3" />
                Pending
              </Badge>
            )}
            {card.agent_state === 'processing' && (
              <Badge variant="outline" className="text-xs font-medium gap-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700">
                <Loader2 className="w-3 h-3 animate-spin" />
                Processing
              </Badge>
            )}
            {card.isBlocked && (
              <Badge variant="outline" className="text-xs font-medium gap-1 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700" title={`${card.blockedByCount || card.dependencies?.length || 0} dependencies chưa hoàn thành`}>
                <Ban className="w-3 h-3" />
                Blocked
              </Badge>
            )}
            {card.age_hours !== undefined && formatAge(card.age_hours) && (
              <Badge variant="outline" className={`text-xs font-medium ${getAgeBadgeColor(card.age_hours)}`} title="Time in current status">
                {formatAge(card.age_hours)}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {card.dependencies && card.dependencies.length > 0 && (
              <div className={`flex items-center gap-1 text-xs font-medium ${card.isBlocked ? 'text-red-600 dark:text-red-400' : 'text-orange-600 dark:text-orange-400'}`} title={`Depends on: ${card.dependencies.join(', ')}`}>
                <Link2 className="w-3.5 h-3.5" />
                <span>{card.dependencies.length}</span>
              </div>
            )}
            {card.story_point !== undefined && card.story_point !== null && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
                <Zap className="w-3.5 h-3.5" />
                <span>{card.story_point}</span>
              </div>
            )}
          </div>
        </div>

        {/* Task Title - Better typography */}
        <h4 className="text-sm font-semibold text-foreground leading-snug line-clamp-2 pr-14">
          {card.content}
        </h4>

        {/* Description (if available) - More space */}
        {card.description && (
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
            {card.description}
          </p>
        )}

        {/* Footer: Task ID, Priority, Assignee - Better separation */}
        <div className="flex items-center justify-between gap-2 pt-0.5 border-t border-border/30">
          <div className="flex items-center gap-2 pt-2">
            {(card.story_code || card.taskId) && (
              <Badge variant="outline" className="text-xs">
                {card.story_code || `#${card.taskId?.slice(0, 8)}`}
              </Badge>
            )}
            {card.rank !== undefined && card.rank !== null && (
              <Badge
                variant="outline"
                className={`text-xs font-medium ${
                  card.rank <= 3
                    ? "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200/50 dark:border-red-800/50"
                    : card.rank <= 7
                      ? "bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-300 border-orange-200/50 dark:border-orange-800/50"
                      : "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 border-blue-200/50 dark:border-blue-800/50"
                }`}
              >
                P{card.rank}
              </Badge>
            )}
          </div>
          {card.assignee_id && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-2">
              <User className="w-3.5 h-3.5" />
              <span className="truncate max-w-[60px] font-medium">
                {card.assignee_id.slice(0, 8)}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Memoized export for performance optimization
// Only re-render when card data, isDragging state, or callbacks change
export const KanbanCard = memo(KanbanCardComponent, (prevProps, nextProps) => {
  // Custom comparison function
  // Re-render if card data changed
  if (prevProps.card.id !== nextProps.card.id) return false
  if (prevProps.card.content !== nextProps.card.content) return false
  if (prevProps.card.description !== nextProps.card.description) return false
  if (prevProps.card.type !== nextProps.card.type) return false
  if (prevProps.card.rank !== nextProps.card.rank) return false
  if (prevProps.card.story_point !== nextProps.card.story_point) return false
  if (prevProps.card.priority !== nextProps.card.priority) return false
  if (prevProps.card.assignee_id !== nextProps.card.assignee_id) return false
  if (prevProps.card.age_hours !== nextProps.card.age_hours) return false
  if (prevProps.card.epic_id !== nextProps.card.epic_id) return false
  if (prevProps.card.updated_at !== nextProps.card.updated_at) return false
  // Check blocked state
  if (prevProps.card.isBlocked !== nextProps.card.isBlocked) return false
  if (prevProps.card.blockedByCount !== nextProps.card.blockedByCount) return false
  // Check agent_state - important for drag-and-drop
  if (prevProps.card.agent_state !== nextProps.card.agent_state) return false
  // Check arrays - important for edit form data sync
  if (JSON.stringify(prevProps.card.dependencies) !== JSON.stringify(nextProps.card.dependencies)) return false
  if (JSON.stringify(prevProps.card.acceptance_criteria) !== JSON.stringify(nextProps.card.acceptance_criteria)) return false
  if (JSON.stringify(prevProps.card.requirements) !== JSON.stringify(nextProps.card.requirements)) return false

  // Re-render if dragging state changed
  if (prevProps.isDragging !== nextProps.isDragging) return false

  // Don't re-render if only callbacks changed (they're memoized)
  return true
})

KanbanCard.displayName = 'KanbanCard'
