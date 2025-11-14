import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, AlertCircle, Clock, User2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Story } from '../../types/board'

interface KanbanCardProps {
  story: Story
  onClick?: (story: Story) => void
}

const PRIORITY_COLORS = {
  HIGH: 'border-l-red-500 bg-red-50/50',
  MEDIUM: 'border-l-amber-500 bg-amber-50/50',
  LOW: 'border-l-blue-500 bg-blue-50/50',
  NONE: 'border-l-gray-300 bg-white',
}

const PRIORITY_LABELS = {
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low',
  NONE: 'None',
}

const TYPE_COLORS = {
  USER_STORY: 'bg-blue-100 text-blue-700',
  ENABLER_STORY: 'bg-purple-100 text-purple-700',
  BUG: 'bg-red-100 text-red-700',
}

const TYPE_LABELS = {
  USER_STORY: 'Story',
  ENABLER_STORY: 'Enabler',
  BUG: 'Bug',
}

export const KanbanCard = ({ story, onClick }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: story.id,
    data: { story },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group bg-white border-2 border-gray-200 border-l-4 rounded-xl p-4 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer',
        PRIORITY_COLORS[story.priority],
        isDragging && 'opacity-50 scale-105 shadow-xl'
      )}
      onClick={() => onClick?.(story)}
    >
      {/* Header */}
      <div className="flex items-start gap-2 mb-3">
        {/* Drag Handle */}
        <button
          {...attributes}
          {...listeners}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors cursor-grab active:cursor-grabbing mt-0.5"
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="h-4 w-4" />
        </button>

        {/* Title */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-gray-900 line-clamp-2 break-words">{story.title}</h4>
        </div>

        {/* Story Points */}
        {story.story_points && (
          <div className="flex-shrink-0 w-6 h-6 rounded-md bg-gray-100 flex items-center justify-center">
            <span className="text-xs font-bold text-gray-700">{story.story_points}</span>
          </div>
        )}
      </div>

      {/* Description */}
      {story.description && (
        <p className="text-xs text-gray-600 line-clamp-2 mb-3 break-words">{story.description}</p>
      )}

      {/* Blocked Status */}
      {story.blocked_reason && (
        <div className="flex items-start gap-1.5 mb-3 p-2 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-3.5 w-3.5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-red-700 font-medium break-words">{story.blocked_reason}</p>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
        {/* Type Badge */}
        <span
          className={cn('px-2 py-0.5 rounded-md text-xs font-semibold', TYPE_COLORS[story.story_type])}
        >
          {TYPE_LABELS[story.story_type]}
        </span>

        {/* Priority Badge */}
        <span className="text-xs text-gray-500 font-medium">{PRIORITY_LABELS[story.priority]}</span>
      </div>

      {/* ID */}
      <div className="mt-2 text-xs text-gray-400 font-mono">#{story.id}</div>
    </div>
  )
}
