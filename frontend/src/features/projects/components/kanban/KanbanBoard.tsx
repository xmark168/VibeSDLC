import { useState } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from '@dnd-kit/core'
import { arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { KanbanColumn } from './KanbanColumn'
import { KanbanCard } from './KanbanCard'
import type { BoardView, Story, BoardColumn } from '../../types/board'
import { Loader2 } from 'lucide-react'

interface KanbanBoardProps {
  boardData: BoardView | null
  isLoading: boolean
  onStoryClick?: (story: Story) => void
  onMoveStory?: (storyId: number, fromStatus: string, toStatus: string) => void
}

export const KanbanBoard = ({
  boardData,
  isLoading,
  onStoryClick,
  onMoveStory,
}: KanbanBoardProps) => {
  const [activeStory, setActiveStory] = useState<Story | null>(null)
  const [columns, setColumns] = useState<BoardColumn[]>(boardData?.columns || [])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start drag
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Update columns when boardData changes
  useState(() => {
    if (boardData) {
      setColumns(boardData.columns)
    }
  })

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const story = active.data.current?.story as Story
    setActiveStory(story)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveStory(null)

    if (!over) return

    const activeStory = active.data.current?.story as Story

    // Get the target column status
    // If dropped on a column, over.id is the column status (string)
    // If dropped on a card, we need to get the column from the card's data
    let overColumnStatus: string

    if (typeof over.id === 'string') {
      // Dropped directly on column
      overColumnStatus = over.id
    } else {
      // Dropped on a card - find which column this card belongs to
      const targetColumn = columns.find(col =>
        col.stories.some(s => s.id === over.id)
      )
      if (!targetColumn) return
      overColumnStatus = targetColumn.status
    }

    // If dropped on same column, do nothing
    if (activeStory.status === overColumnStatus) return

    // Update UI optimistically
    const newColumns = columns.map((col) => {
      // Remove from old column
      if (col.status === activeStory.status) {
        return {
          ...col,
          stories: col.stories.filter((s) => s.id !== activeStory.id),
          current_count: col.current_count - 1,
        }
      }
      // Add to new column
      if (col.status === overColumnStatus) {
        return {
          ...col,
          stories: [...col.stories, { ...activeStory, status: col.status }],
          current_count: col.current_count + 1,
        }
      }
      return col
    })

    setColumns(newColumns)

    // Call parent handler
    onMoveStory?.(activeStory.id, activeStory.status, overColumnStatus)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-2xl border-2 border-gray-200">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto" />
          <p className="text-sm text-gray-600 font-medium">Loading board...</p>
        </div>
      </div>
    )
  }

  if (!boardData) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-2xl border-2 border-gray-200">
        <div className="text-center space-y-3 px-4">
          <div className="w-16 h-16 mx-auto bg-gray-200 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-700">No board data</h3>
            <p className="text-sm text-gray-500 mt-1">Create stories to see them on the board</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="h-full overflow-x-auto pb-4">
        <div className="flex gap-4 h-full min-w-max p-1">
          {columns.map((column) => (
            <KanbanColumn
              key={column.status}
              column={column}
              onCardClick={onStoryClick}
            />
          ))}
        </div>
      </div>

      {/* Drag Overlay */}
      <DragOverlay>
        {activeStory && (
          <div className="rotate-3 scale-105">
            <KanbanCard story={activeStory} />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  )
}
