
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { KanbanColumn, type KanbanColumnData } from "./kanban-column"
import { TaskDetailModal } from "./task-detail-modal"
import type { KanbanCardData } from "./kanban-card"
import { useKanbanBoard } from "@/queries/backlog-items"

interface KanbanBoardProps {
  kanbanData?: any
  projectId?: string
  sprintId?: string
}

const initialColumns: KanbanColumnData[] = [
  { id: "backlog", title: "Backlog", color: "border-yellow-500", cards: [] },
  { id: "todo", title: "ToDo", color: "border-purple-500", cards: [] },
  { id: "inprogress", title: "InProgress", color: "border-red-500", cards: [] },
  { id: "review", title: "Review", color: "border-blue-500", cards: [] },
  { id: "testing", title: "Testing", color: "border-pink-500", cards: [] },
  { id: "done", title: "Done", color: "border-cyan-500", cards: [] },
]

export function KanbanBoard({ kanbanData, projectId, sprintId }: KanbanBoardProps) {
  const [columns, setColumns] = useState<KanbanColumnData[]>(initialColumns)
  const [draggedCard, setDraggedCard] = useState<KanbanCardData | null>(null)
  const [draggedOverColumn, setDraggedOverColumn] = useState<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<KanbanCardData | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Load initial data from database
  const { data: dbKanbanData, isLoading } = useKanbanBoard(sprintId)

  // Reset columns when sprintId changes
  useEffect(() => {
    if (!sprintId) {
      setColumns(initialColumns)
    }
  }, [sprintId])

  // Load initial data from database when component mounts
  useEffect(() => {
    if (dbKanbanData && dbKanbanData.board) {
      console.log('[KanbanBoard] Loading Kanban board from database:', dbKanbanData)

      const newColumns: KanbanColumnData[] = [
        {
          id: "backlog",
          title: "Backlog",
          color: "border-yellow-500",
          cards: (dbKanbanData.board.Backlog || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "backlog",
            taskId: item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "todo",
          title: "ToDo",
          color: "border-purple-500",
          cards: (dbKanbanData.board.Todo || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "todo",
            taskId: item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "inprogress",
          title: "InProgress",
          color: "border-red-500",
          cards: (dbKanbanData.board.Doing || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "inprogress",
            taskId: item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "done",
          title: "Done",
          color: "border-cyan-500",
          cards: (dbKanbanData.board.Done || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "done",
            taskId: item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
      ]

      setColumns(newColumns)
    }
  }, [dbKanbanData])

  // Update columns when WebSocket kanbanData changes (real-time updates)
  useEffect(() => {
    if (kanbanData && kanbanData.kanban_board) {
      console.log('Updating Kanban board with WebSocket data:', kanbanData)

      // Map kanban_board data to columns
      const newColumns: KanbanColumnData[] = [
        {
          id: "backlog",
          title: "Backlog",
          color: "border-yellow-500",
          cards: (kanbanData.kanban_board.Backlog || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "backlog",
            taskId: item.item_id || item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "todo",
          title: "ToDo",
          color: "border-purple-500",
          cards: (kanbanData.kanban_board.Todo || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "todo",
            taskId: item.item_id || item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "inprogress",
          title: "InProgress",
          color: "border-red-500",
          cards: (kanbanData.kanban_board.Doing || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "inprogress",
            taskId: item.item_id || item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
        {
          id: "done",
          title: "Done",
          color: "border-cyan-500",
          cards: (kanbanData.kanban_board.Done || []).map((item: any) => ({
            id: item.id,
            content: item.title,
            columnId: "done",
            taskId: item.item_id || item.id,
            description: item.description,
            status: item.status,
            type: item.type,
            story_point: item.story_point,
            estimate_value: item.estimate_value,
            rank: item.rank,
            assignee_id: item.assignee_id,
            reviewer_id: item.reviewer_id,
          }))
        },
      ]

      setColumns(newColumns)
    }
  }, [kanbanData])

  const handleWheel = (e: React.WheelEvent) => {
    if (scrollContainerRef.current) {
      e.preventDefault()
      scrollContainerRef.current.scrollLeft += e.deltaY + 1
    }
  }

  const handleDownloadResult = (card: KanbanCardData) => {
    if (!card.result) return

    const blob = new Blob([card.result], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `task-${card.taskId || card.id}-result.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleAddCard = (columnId: string, content: string) => {
    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === columnId) {
          return {
            ...col,
            cards: [
              ...col.cards,
              {
                id: Date.now().toString(),
                content,
                columnId,
                agentName: "Agent Smith",
                agentAvatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${Date.now()}`,
                taskId: `T${Math.floor(Math.random() * 10000)}`,
                result: `# Task Result\n\nThis is the result of the task: ${content}`,
                subtasks: ["Subtask 1", "Subtask 2"],
                branch: "feature/task-" + Date.now(),
              },
            ],
          }
        }
        return col
      }),
    )
  }

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === columnId) {
          return {
            ...col,
            cards: col.cards.filter((card) => card.id !== cardId),
          }
        }
        return col
      }),
    )
  }

  const handleDragStart = (card: KanbanCardData) => {
    setDraggedCard(card)
  }

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault()
    setDraggedOverColumn(columnId)
  }

  const handleDragLeave = () => {
    setDraggedOverColumn(null)
  }

  const handleDrop = (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault()
    if (!draggedCard) return

    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === draggedCard.columnId) {
          return {
            ...col,
            cards: col.cards.filter((card) => card.id !== draggedCard.id),
          }
        }
        if (col.id === targetColumnId) {
          return {
            ...col,
            cards: [...col.cards, { ...draggedCard, columnId: targetColumnId }],
          }
        }
        return col
      }),
    )

    setDraggedCard(null)
    setDraggedOverColumn(null)
  }

  const handleDragEnd = () => {
    setDraggedCard(null)
    setDraggedOverColumn(null)
  }

  return (
    <>
      <div
        ref={scrollContainerRef}
        onWheel={handleWheel}
        className="h-full overflow-x-auto bg-background p-6 border-t"
        style={{ scrollBehavior: "smooth" }}
      >
        <div className="flex gap-4 min-w-max">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              isDraggedOver={draggedOverColumn === column.id}
              draggedCardId={draggedCard?.id}
              onDragOver={(e) => handleDragOver(e, column.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, column.id)}
              onCardDragStart={handleDragStart}
              onCardDragEnd={handleDragEnd}
              onCardClick={setSelectedCard}
              onCardDelete={(cardId) => handleDeleteCard(column.id, cardId)}
              onCardDownloadResult={handleDownloadResult}
              onAddCard={(content) => handleAddCard(column.id, content)}
            />
          ))}
        </div>
      </div>

      <TaskDetailModal
        card={selectedCard}
        open={!!selectedCard}
        onOpenChange={() => setSelectedCard(null)}
        onDownloadResult={handleDownloadResult}
      />
    </>
  )
}
