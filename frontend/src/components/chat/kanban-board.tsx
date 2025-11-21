
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Settings, Activity, Shield, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { KanbanColumn, type KanbanColumnData } from "./kanban-column"
import { TaskDetailModal } from "./task-detail-modal"
import { WIPLimitSettingsDialog } from "./wip-limit-settings-dialog"
import { FlowMetricsDashboard } from "./flow-metrics-dashboard"
import { PolicyValidationDialog, type PolicyViolation } from "./policy-validation-dialog"
import { PolicySettingsDialog } from "./policy-settings-dialog"
import { AgingItemsAlert } from "./aging-items-alert"
import { BottleneckAlert } from "./bottleneck-alert"
import { CumulativeFlowDiagram } from "./cumulative-flow-diagram"
import type { KanbanCardData } from "./kanban-card"
import { useKanbanBoard } from "@/queries/backlog-items"
import { backlogItemsApi } from "@/apis/backlog-items"

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
  const [showPolicySettings, setShowPolicySettings] = useState(false)
  const [showCFD, setShowCFD] = useState(false)
  const [policyViolation, setPolicyViolation] = useState<PolicyViolation | null>(null)
  const [flowMetrics, setFlowMetrics] = useState<any>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Load initial data from database
  const { data: dbKanbanData, isLoading } = useKanbanBoard(projectId)

  // Load flow metrics for alerts
  useEffect(() => {
    if (projectId) {
      loadFlowMetrics()
      // Refresh metrics every 5 minutes
      const interval = setInterval(loadFlowMetrics, 5 * 60 * 1000)
      return () => clearInterval(interval)
    }
  }, [projectId])

  const loadFlowMetrics = async () => {
    if (!projectId) return
    try {
      const metrics = await backlogItemsApi.getFlowMetrics(projectId, 30)
      setFlowMetrics(metrics)
    } catch (error) {
      console.error('Failed to load flow metrics:', error)
    }
  }

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

  const handleDrop = async (e: React.DragEvent, targetColumnId: string) => {
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

    // ===== Policy Validation =====
    // Validate workflow policies before moving cards if projectId and taskId exist
    if (projectId && draggedCard.taskId) {
      try {
        const fromStatus = draggedCard.columnId.charAt(0).toUpperCase() + draggedCard.columnId.slice(1)
        const toStatus = targetColumnId.charAt(0).toUpperCase() + targetColumnId.slice(1)

        const policyValidation = await backlogItemsApi.validatePolicyMove(
          projectId,
          draggedCard.taskId,
          fromStatus,
          toStatus
        )

        // If policy violations exist, block the move and show dialog
        if (!policyValidation.allowed && policyValidation.violations.length > 0) {
          setPolicyViolation({
            error: 'POLICY_VIOLATION',
            message: 'Workflow policy not satisfied',
            violations: policyValidation.violations,
            policy: { from: fromStatus, to: toStatus }
          })
          setDraggedCard(null)
          setDraggedOverColumn(null)
          return
        }
      } catch (error) {
        console.error('Policy validation error:', error)
        // Continue with move if validation fails (fail-open for better UX)
      }
    }

    // ===== WIP Limit Check =====
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
        {/* Header with Settings Buttons */}
        <div className="flex items-center justify-between px-6 pt-4 pb-2">
          <h2 className="text-lg font-semibold text-foreground">Kanban Board</h2>
          {projectId && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCFD(true)}
                className="gap-2"
              >
                <TrendingUp className="w-4 h-4" />
                CFD
              </Button>
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
                onClick={() => setShowPolicySettings(true)}
                className="gap-2"
              >
                <Shield className="w-4 h-4" />
                Policies
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

        {/* Lean Kanban Alerts */}
        {projectId && flowMetrics && (
          <div className="px-6">
            <AgingItemsAlert
              projectId={projectId}
              agingItems={flowMetrics.aging_items || []}
              onCardClick={(itemId) => {
                // Find and select the card
                const allCards = columns.flatMap(col => col.cards)
                const card = allCards.find(c => c.taskId === itemId || c.id === itemId)
                if (card) setSelectedCard(card)
              }}
            />
            <BottleneckAlert
              bottlenecks={flowMetrics.bottlenecks || {}}
              threshold={48}
            />
          </div>
        )}

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

      <PolicySettingsDialog
        projectId={projectId}
        open={showPolicySettings}
        onOpenChange={setShowPolicySettings}
      />

      <CumulativeFlowDiagram
        projectId={projectId}
        open={showCFD}
        onOpenChange={setShowCFD}
      />
    </>
  )
}
