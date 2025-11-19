
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Settings, Activity } from "lucide-react"
import { Button } from "@/components/ui/button"
import { KanbanColumn, type KanbanColumnData } from "./kanban-column"
import { TaskDetailModal } from "./task-detail-modal"
import { WIPLimitSettingsDialog } from "./wip-limit-settings-dialog"
import { FlowMetricsDashboard } from "./flow-metrics-dashboard"
import { PolicyValidationDialog, type PolicyViolation } from "./policy-validation-dialog"
import type { KanbanCardData } from "./kanban-card"
import { useKanbanBoard } from "@/queries/backlog-items"

interface KanbanBoardProps {
  kanbanData?: any
  projectId?: string
}

const initialColumns: KanbanColumnData[] = [
  { id: "todo", title: "ToDo", color: "border-purple-500", cards: [] },
  { id: "inprogress", title: "InProgress", color: "border-red-500", cards: [] },
  { id: "review", title: "Review", color: "border-blue-500", cards: [] },
  { id: "testing", title: "Testing", color: "border-pink-500", cards: [] },
  { id: "done", title: "Done", color: "border-cyan-500", cards: [] },
]

export function KanbanBoard({ kanbanData, projectId }: KanbanBoardProps) {
  const [columns, setColumns] = useState<KanbanColumnData[]>(initialColumns)
  const [draggedCard, setDraggedCard] = useState<KanbanCardData | null>(null)
  const [draggedOverColumn, setDraggedOverColumn] = useState<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<KanbanCardData | null>(null)
  const [showWIPSettings, setShowWIPSettings] = useState(false)
  const [showFlowMetrics, setShowFlowMetrics] = useState(false)
  const [policyViolation, setPolicyViolation] = useState<PolicyViolation | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Load initial data from database
  const { data: dbKanbanData, isLoading } = useKanbanBoard(projectId)

  // Reset columns when projectId changes
  useEffect(() => {
    if (!projectId) {
      setColumns(initialColumns)
    }
  }, [projectId])

  // Load initial data from database when component mounts
  useEffect(() => {
    if (dbKanbanData && dbKanbanData.board) {
      console.log('[KanbanBoard] Loading Kanban board from database:', dbKanbanData)

      // TraDS ============= Kanban Hierarchy: Filter out Epics and Sub-tasks from board display
      const filterItems = (items: any[]) => items.filter((item: any) =>
        item.type !== "Epic" && item.type !== "Sub-task"
      )

      // TraDS ============= Kanban Hierarchy: Map items with parent/children relationships
      const mapItem = (item: any, columnId: string) => ({
        id: item.id,
        content: item.title,
        columnId,
        taskId: item.id,
        description: item.description,
        status: item.status,
        type: item.type,
        story_point: item.story_point,
        estimate_value: item.estimate_value,
        rank: item.rank,
        assignee_id: item.assignee_id,
        reviewer_id: item.reviewer_id,
        parent: item.parent ? {
          id: item.parent.id,
          content: item.parent.title,
          columnId: item.parent.status?.toLowerCase() || "",
          taskId: item.parent.id,
          type: item.parent.type,
          title: item.parent.title,
        } : undefined,
        children: item.children ? item.children.map((child: any) => ({
          id: child.id,
          content: child.title,
          columnId: child.status?.toLowerCase() || "",
          taskId: child.id,
          description: child.description,
          status: child.status,
          type: child.type,
          story_point: child.story_point,
          estimate_value: child.estimate_value,
          rank: child.rank,
          assignee_id: child.assignee_id,
          reviewer_id: child.reviewer_id,
          title: child.title,
        })) : [],
      })

      const newColumns: KanbanColumnData[] = [
        {
          id: "todo",
          title: "ToDo",
          color: "border-purple-500",
          cards: filterItems(dbKanbanData.board.Todo || []).map((item: any) => mapItem(item, "todo")),
          wipLimit: dbKanbanData.wip_limits?.Todo?.wip_limit,
          limitType: dbKanbanData.wip_limits?.Todo?.limit_type
        },
        {
          id: "inprogress",
          title: "InProgress",
          color: "border-red-500",
          cards: filterItems(dbKanbanData.board.InProgress || dbKanbanData.board.Doing || []).map((item: any) => mapItem(item, "inprogress")),
          wipLimit: dbKanbanData.wip_limits?.InProgress?.wip_limit,
          limitType: dbKanbanData.wip_limits?.InProgress?.limit_type
        },
        {
          id: "review",
          title: "Review",
          color: "border-blue-500",
          cards: filterItems(dbKanbanData.board.Review || []).map((item: any) => mapItem(item, "review")),
          wipLimit: dbKanbanData.wip_limits?.Review?.wip_limit,
          limitType: dbKanbanData.wip_limits?.Review?.limit_type
        },
        {
          id: "done",
          title: "Done",
          color: "border-cyan-500",
          cards: filterItems(dbKanbanData.board.Done || []).map((item: any) => mapItem(item, "done")),
          wipLimit: dbKanbanData.wip_limits?.Done?.wip_limit,
          limitType: dbKanbanData.wip_limits?.Done?.limit_type
        },
      ]

      setColumns(newColumns)
    }
  }, [dbKanbanData])

  // Update columns when WebSocket kanbanData changes (real-time updates)
  useEffect(() => {
    if (kanbanData && kanbanData.kanban_board) {
      console.log('Updating Kanban board with WebSocket data:', kanbanData)

      // TraDS ============= Kanban Hierarchy: Filter out Epics and Sub-tasks from board display
      const filterItems = (items: any[]) => items.filter((item: any) =>
        item.type !== "Epic" && item.type !== "Sub-task"
      )

      // TraDS ============= Kanban Hierarchy: Map items with parent/children relationships
      const mapItem = (item: any, columnId: string) => ({
        id: item.id,
        content: item.title,
        columnId,
        taskId: item.item_id || item.id,
        description: item.description,
        status: item.status,
        type: item.type,
        story_point: item.story_point,
        estimate_value: item.estimate_value,
        rank: item.rank,
        assignee_id: item.assignee_id,
        reviewer_id: item.reviewer_id,
        parent: item.parent ? {
          id: item.parent.id,
          content: item.parent.title,
          columnId: item.parent.status?.toLowerCase() || "",
          taskId: item.parent.id,
          type: item.parent.type,
          title: item.parent.title,
        } : undefined,
        children: item.children ? item.children.map((child: any) => ({
          id: child.id,
          content: child.title,
          columnId: child.status?.toLowerCase() || "",
          taskId: child.id,
          description: child.description,
          status: child.status,
          type: child.type,
          story_point: child.story_point,
          estimate_value: child.estimate_value,
          rank: child.rank,
          assignee_id: child.assignee_id,
          reviewer_id: child.reviewer_id,
          title: child.title,
        })) : [],
      })

      const newColumns: KanbanColumnData[] = [
        {
          id: "todo",
          title: "ToDo",
          color: "border-purple-500",
          cards: filterItems(kanbanData.kanban_board.Todo || []).map((item: any) => mapItem(item, "todo"))
        },
        {
          id: "inprogress",
          title: "InProgress",
          color: "border-red-500",
          cards: filterItems(kanbanData.kanban_board.Doing || []).map((item: any) => mapItem(item, "inprogress"))
        },
        {
          id: "done",
          title: "Done",
          color: "border-cyan-500",
          cards: filterItems(kanbanData.kanban_board.Done || []).map((item: any) => mapItem(item, "done"))
        },
      ]

      setColumns(newColumns)
    }
  }, [kanbanData])

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

    // Find target column
    const targetColumn = columns.find(col => col.id === targetColumnId)
    if (!targetColumn) return

    // Skip if dropping in the same column
    if (draggedCard.columnId === targetColumnId) {
      setDraggedCard(null)
      setDraggedOverColumn(null)
      return
    }

    // Check WIP limit enforcement
    if (targetColumn.wipLimit) {
      const currentCount = targetColumn.cards.length
      const isMovingFromThisColumn = draggedCard.columnId === targetColumnId

      // If moving from different column, count will increase
      if (!isMovingFromThisColumn && currentCount >= targetColumn.wipLimit) {
        // WIP limit exceeded
        if (targetColumn.limitType === 'hard') {
          // Hard limit: block the move
          alert(`Cannot move to ${targetColumn.title}: WIP limit (${targetColumn.wipLimit}) exceeded!\n\nCurrent items: ${currentCount}\n\nPlease move items out of ${targetColumn.title} before adding more.`)
          setDraggedCard(null)
          setDraggedOverColumn(null)
          return
        } else {
          // Soft limit: warn but allow
          const confirmed = confirm(
            `Warning: Moving to ${targetColumn.title} will exceed WIP limit (${targetColumn.wipLimit}).\n\nCurrent items: ${currentCount}\n\nDo you want to proceed anyway?`
          )
          if (!confirmed) {
            setDraggedCard(null)
            setDraggedOverColumn(null)
            return
          }
        }
      }
    }

    // TODO: Policy Validation Integration
    // To validate workflow policies before moving cards:
    //
    // 1. Call the validation API before proceeding with the move:
    //    const validation = await backlogItemsApi.validateStoryMove(
    //      projectId,
    //      draggedCard.taskId,
    //      targetColumnId.toUpperCase()
    //    )
    //
    // 2. Check if move is allowed:
    //    if (!validation.allowed && validation.violation?.error === 'POLICY_VIOLATION') {
    //      setPolicyViolation(validation.violation)
    //      setDraggedCard(null)
    //      setDraggedOverColumn(null)
    //      return
    //    }
    //
    // 3. The PolicyValidationDialog will automatically show when policyViolation is set
    //
    // Example violation format from backend:
    // {
    //   error: "POLICY_VIOLATION",
    //   message: "Workflow policy not satisfied",
    //   violations: [
    //     "Story must have an assignee",
    //     "Story points must be estimated"
    //   ],
    //   policy: { from: "Todo", to: "InProgress" }
    // }

    // Proceed with the move
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
        className="h-full overflow-x-auto bg-background border-t flex flex-col"
        style={{ scrollBehavior: "smooth" }}
      >
        {/* Header with WIP Settings Button */}
        <div className="flex items-center justify-between px-6 pt-4 pb-2">
          <h2 className="text-lg font-semibold text-foreground">Kanban Board</h2>
          {projectId && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFlowMetrics(true)}
                className="gap-2"
              >
                <Activity className="w-4 h-4" />
                Metrics
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowWIPSettings(true)}
                className="gap-2"
              >
                <Settings className="w-4 h-4" />
                WIP Limits
              </Button>
            </div>
          )}
        </div>

        {/* Columns */}
        <div className="flex gap-4 min-w-max px-6 pb-6">
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

      <WIPLimitSettingsDialog
        projectId={projectId}
        open={showWIPSettings}
        onOpenChange={setShowWIPSettings}
      />

      <FlowMetricsDashboard
        projectId={projectId}
        open={showFlowMetrics}
        onOpenChange={setShowFlowMetrics}
      />

      <PolicyValidationDialog
        violation={policyViolation}
        cardTitle={draggedCard?.content}
        open={!!policyViolation}
        onOpenChange={(open) => !open && setPolicyViolation(null)}
      />
    </>
  )
}
