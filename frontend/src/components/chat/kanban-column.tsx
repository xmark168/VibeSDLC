import type React from "react"
import { memo } from "react"
import { KanbanCard, type KanbanCardData } from "./kanban-card"

export type KanbanColumnData = {
  id: string
  title: string
  color: string
  cards: KanbanCardData[]
  wipLimit?: number  // WIP limit for this column
  limitType?: 'hard' | 'soft'  // Hard or soft limit
}

interface KanbanColumnProps {
  column: KanbanColumnData
  isDraggedOver?: boolean
  draggedCardId?: string | null
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: () => void
  onDrop: (e: React.DragEvent) => void
  onCardDragStart: (card: KanbanCardData) => void
  onCardDragEnd: () => void
  onCardClick: (card: KanbanCardData) => void
  onCardDelete: (cardId: string) => void
  onCardDownloadResult: (card: KanbanCardData) => void
  onCardDuplicate?: (cardId: string) => void
  onCardMove?: (cardId: string, targetColumn: string) => void
  onCardEdit?: (card: KanbanCardData) => void
}

function KanbanColumnComponent({
  column,
  isDraggedOver,
  draggedCardId,
  onDragOver,
  onDragLeave,
  onDrop,
  onCardDragStart,
  onCardDragEnd,
  onCardClick,
  onCardDelete,
  onCardDownloadResult,
  onCardDuplicate,
  onCardMove,
  onCardEdit,
}: KanbanColumnProps) {

  // Calculate WIP utilization for styling - Modern & Minimal: Softer colors
  const getWIPBadgeStyle = () => {
    if (!column.wipLimit) return "bg-slate-100 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300 font-medium"

    const currentCount = column.cards.length
    const limit = column.wipLimit
    const utilization = currentCount / limit

    if (currentCount >= limit) {
      return "bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 font-semibold border border-red-200/50 dark:border-red-800/50"
    } else if (utilization >= 0.8) {
      return "bg-orange-50 dark:bg-orange-950/50 text-orange-700 dark:text-orange-300 font-medium border border-orange-200/50 dark:border-orange-800/50"
    } else {
      return "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200/50 dark:border-emerald-800/50"
    }
  }

  return (
    <div
      className="w-72 flex-shrink-0"
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Column Header - Modern & Minimal */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border/40">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-foreground tracking-tight">
            {column.title}
          </h3>
          <span className={`text-xs px-2.5 py-1 rounded-lg ${getWIPBadgeStyle()}`}>
            {column.wipLimit
              ? `${column.cards.length}/${column.wipLimit}`
              : column.cards.length
            }
          </span>
        </div>
        {column.wipLimit && column.cards.length >= column.wipLimit && (
          <span className="text-sm" title="WIP limit reached">
            🚫
          </span>
        )}
      </div>

      <div
        className={`
          space-y-3 min-h-[100px] rounded-xl p-3
          transition-all duration-200
          ${isDraggedOver ? "bg-muted/30 border-2 border-dashed border-border" : "border-2 border-transparent"}
        `}
      >
        {/* Cards */}
        {column.cards.map((card) => (
          <KanbanCard
            key={card.id}
            card={card}
            isDragging={draggedCardId === card.id}
            onDragStart={() => onCardDragStart(card)}
            onDragEnd={onCardDragEnd}
            onClick={() => onCardClick(card)}
            onDelete={() => onCardDelete(card.id)}
            onDownloadResult={() => onCardDownloadResult(card)}
            onDuplicate={onCardDuplicate ? () => onCardDuplicate(card.id) : undefined}
            onMove={onCardMove ? (targetColumn) => onCardMove(card.id, targetColumn) : undefined}
            onEdit={onCardEdit ? () => onCardEdit(card) : undefined}
          />
        ))}
      </div>

      {/* Remove dialog from column - it's now at board level */}
    </div>
  )
}

// Memoized export for performance optimization
// Only re-render when column data or state changes
export const KanbanColumn = memo(KanbanColumnComponent, (prevProps, nextProps) => {
  // Custom comparison function
  // Re-render if column ID changed (shouldn't happen but safety check)
  if (prevProps.column.id !== nextProps.column.id) return false

  // Re-render if cards array changed (length or content)
  if (prevProps.column.cards.length !== nextProps.column.cards.length) return false

  // Re-render if any card data changed (check IDs as quick proxy)
  const prevCardIds = prevProps.column.cards.map(c => c.id).join(',')
  const nextCardIds = nextProps.column.cards.map(c => c.id).join(',')
  if (prevCardIds !== nextCardIds) return false

  // Re-render if drag state changed
  if (prevProps.isDraggedOver !== nextProps.isDraggedOver) return false
  if (prevProps.draggedCardId !== nextProps.draggedCardId) return false

  // Re-render if WIP limits changed
  if (prevProps.column.wipLimit !== nextProps.column.wipLimit) return false
  if (prevProps.column.limitType !== nextProps.column.limitType) return false

  // Don't re-render if only callbacks changed (they're memoized)
  return true
})

KanbanColumn.displayName = 'KanbanColumn'
