import { X, Eye } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

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
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={`bg-card rounded-lg border border-border p-3 group relative hover:shadow-md transition-all cursor-pointer ${
        isDragging ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <Avatar className="w-10 h-10 flex-shrink-0">
          <AvatarImage src={card.agentAvatar || "/placeholder.svg"} alt={card.agentName} />
          <AvatarFallback className="bg-primary/10 text-primary text-xs">
            {card.agentName?.charAt(0) || "A"}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 min-w-0">
          {/* Task Title */}
          <h4 className="text-sm font-medium text-foreground mb-2 line-clamp-2">{card.content}</h4>

          {/* Agent Name Tag and Task ID */}
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs px-2 py-1 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 truncate">
              {card.agentName}
            </span>
            <span className="text-xs text-muted-foreground">id:{card.taskId}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {card.result && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDownloadResult()
            }}
            className="p-1.5 rounded hover:bg-muted"
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
          className="p-1.5 rounded hover:bg-muted"
        >
          <X className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
        </button>
      </div>
    </div>
  )
}
