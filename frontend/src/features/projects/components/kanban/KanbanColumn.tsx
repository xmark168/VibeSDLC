import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { KanbanCard } from './KanbanCard'
import type { BoardColumn, Story } from '../../types/board'

interface KanbanColumnProps {
  column: BoardColumn
  onCardClick?: (story: Story) => void
}

const STATUS_COLORS = {
  TODO: 'bg-gray-100 border-gray-300',
  IN_PROGRESS: 'bg-blue-100 border-blue-300',
  REVIEW: 'bg-purple-100 border-purple-300',
  TESTING: 'bg-amber-100 border-amber-300',
  DONE: 'bg-green-100 border-green-300',
  BLOCKED: 'bg-red-100 border-red-300',
  ARCHIVED: 'bg-slate-100 border-slate-300',
}

export const KanbanColumn = ({ column, onCardClick }: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({
    id: column.status,
    data: { column },
  })

  const isWIPLimitExceeded = column.wip_limit !== null && column.current_count > column.wip_limit
  const isWIPLimitWarning =
    column.wip_limit !== null && !isWIPLimitExceeded && column.current_count >= column.wip_limit * 0.8

  return (
    <div
      className={cn(
        'flex flex-col bg-gray-50 border-2 rounded-xl p-4 h-full min-w-[320px] transition-all duration-200',
        isOver ? 'border-blue-500 bg-blue-50 shadow-lg' : 'border-gray-200'
      )}
    >
      {/* Column Header */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-gray-900">{column.name}</h3>
            <div
              className={cn(
                'px-2 py-0.5 rounded-full text-xs font-semibold',
                STATUS_COLORS[column.status]
              )}
            >
              {column.stories.length}
            </div>
          </div>

          {/* WIP Limit Badge */}
          {column.wip_limit !== null && (
            <div
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold',
                isWIPLimitExceeded
                  ? 'bg-red-100 text-red-700 border border-red-300'
                  : isWIPLimitWarning
                    ? 'bg-amber-100 text-amber-700 border border-amber-300'
                    : 'bg-gray-100 text-gray-700 border border-gray-300'
              )}
            >
              {isWIPLimitExceeded && <AlertTriangle className="h-3 w-3" />}
              <span>
                {column.current_count} / {column.wip_limit}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Stories List */}
      <div
        ref={setNodeRef}
        className={cn(
          'flex-1 overflow-y-auto space-y-3 pr-1',
          'scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent'
        )}
      >
        <SortableContext items={column.stories.map((s) => s.id)} strategy={verticalListSortingStrategy}>
          {column.stories.length === 0 ? (
            <div className="flex items-center justify-center h-32 border-2 border-dashed border-gray-300 rounded-xl bg-white/50">
              <p className="text-sm text-gray-500">No stories</p>
            </div>
          ) : (
            column.stories.map((story) => <KanbanCard key={story.id} story={story} onClick={onCardClick} />)
          )}
        </SortableContext>
      </div>
    </div>
  )
}
