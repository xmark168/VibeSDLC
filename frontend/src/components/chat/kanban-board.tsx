import type React from "react"

import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Settings, Activity, Shield, TrendingUp, Search, Filter, X, Plus, BarChart3 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { KanbanColumn, type KanbanColumnData } from "./kanban-column"
import { TaskDetailModal } from "./task-detail-modal"
import { FlowMetricsDashboard } from "./flow-metrics-dashboard"
import { PolicyValidationDialog, type PolicyViolation } from "./policy-validation-dialog"
import { PolicySettingsDialog } from "./policy-settings-dialog"
import { AgingItemsAlert } from "./aging-items-alert"
import { BottleneckAlert } from "./bottleneck-alert"
import { CumulativeFlowDiagram } from "./cumulative-flow-diagram"
import type { KanbanCardData } from "./kanban-card"
import { CreateStoryDialog, type StoryFormData, type StoryEditData } from "./create-story-dialog"
import { useKanbanBoard } from "@/queries/backlog-items"
import { backlogItemsApi } from "@/apis/backlog-items"
import { storiesApi } from "@/apis/stories"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"

interface KanbanBoardProps {
  kanbanData?: any
  projectId?: string
}

const initialColumns: KanbanColumnData[] = [
  { id: "todo", title: "ToDo", color: "border-purple-500", cards: [] },
  { id: "inprogress", title: "InProgress", color: "border-red-500", cards: [] },
  { id: "review", title: "Review", color: "border-blue-500", cards: [] },
  { id: "done", title: "Done", color: "border-cyan-500", cards: [] },
  { id: "archived", title: "Archived", color: "border-gray-400", cards: [] },
]

export function KanbanBoard({ kanbanData, projectId }: KanbanBoardProps) {
  const [columns, setColumns] = useState<KanbanColumnData[]>(initialColumns)
  const [draggedCard, setDraggedCard] = useState<KanbanCardData | null>(null)
  const [draggedOverColumn, setDraggedOverColumn] = useState<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<KanbanCardData | null>(null)
  const [showFlowMetrics, setShowFlowMetrics] = useState(false)
  const [showPolicySettings, setShowPolicySettings] = useState(false)
  const [showCFD, setShowCFD] = useState(false)
  const [showCreateStoryDialog, setShowCreateStoryDialog] = useState(false)
  const [editingStory, setEditingStory] = useState<StoryEditData | null>(null)
  const [policyViolation, setPolicyViolation] = useState<PolicyViolation | null>(null)
  const [flowMetrics, setFlowMetrics] = useState<any>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Search and Filter state
  const [searchQuery, setSearchQuery] = useState("")
  const [showFilters, setShowFilters] = useState(false)
  const [selectedFilters, setSelectedFilters] = useState<{
    types: string[]
    priorities: string[]
  }>({
    types: [],
    priorities: []
  })

  // Keyboard shortcuts state
  const [focusedCardId, setFocusedCardId] = useState<string | null>(null)

  // Load initial data from database
  const { data: dbKanbanData, isLoading, dataUpdatedAt } = useKanbanBoard(projectId)
  const queryClient = useQueryClient()

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

  // Sync selectedCard with updated data from columns
  useEffect(() => {
    if (selectedCard) {
      const allCards = columns.flatMap(col => col.cards)
      const updatedCard = allCards.find(c => c.id === selectedCard.id)
      if (updatedCard && JSON.stringify(updatedCard) !== JSON.stringify(selectedCard)) {
        setSelectedCard(updatedCard)
      }
    }
  }, [columns, selectedCard])

  // Sync editingStory with updated data from columns
  useEffect(() => {
    if (editingStory && showCreateStoryDialog) {
      const allCards = columns.flatMap(col => col.cards)
      const updatedCard = allCards.find(c => c.id === editingStory.id)
      if (updatedCard) {
        const storyType = updatedCard.type?.toLowerCase() === "enablerstory" ? "EnablerStory" : "UserStory"
        const newEditingStory: StoryEditData = {
          id: updatedCard.id,
          title: updatedCard.content,
          description: updatedCard.description,
          type: storyType,
          story_point: updatedCard.story_point,
          priority: updatedCard.priority,
          rank: updatedCard.rank,
          acceptance_criteria: updatedCard.acceptance_criteria,
          requirements: updatedCard.requirements,
          dependencies: updatedCard.dependencies,
          epic_id: updatedCard.epic_id
        }
        if (JSON.stringify(newEditingStory) !== JSON.stringify(editingStory)) {
          setEditingStory(newEditingStory)
        }
      }
    }
  }, [columns, editingStory, showCreateStoryDialog])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      // Get all cards (flattened from columns)
      const allCards = columns.flatMap(col => col.cards)

      // Find currently focused card
      const focusedCard = focusedCardId ? allCards.find(c => c.id === focusedCardId) : null

      switch (e.key.toLowerCase()) {
        case 'e':
          // Edit card
          if (focusedCard) {
            e.preventDefault()
            handleEditCard(focusedCard)
          }
          break
        case 'd':
          // Duplicate card
          if (focusedCard) {
            e.preventDefault()
            handleDuplicateCard(focusedCard.id)
          }
          break
        case 'delete':
        case 'backspace':
          // Delete card
          if (focusedCard && !e.metaKey && !e.ctrlKey) {
            e.preventDefault()
            const column = columns.find(col => col.cards.some(c => c.id === focusedCard.id))
            if (column) {
              handleDeleteCard(column.id, focusedCard.id)
              setFocusedCardId(null)
            }
          }
          break
        case 'escape':
          // Clear focus
          e.preventDefault()
          setFocusedCardId(null)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [focusedCardId, columns])

  // Load initial data from database when component mounts
  useEffect(() => {
    if (dbKanbanData && dbKanbanData.board) {
      console.log('[KanbanBoard] Loading Kanban board from database:', dbKanbanData)
      console.log('[KanbanBoard] Board data counts:', {
        Todo: dbKanbanData.board.Todo?.length || 0,
        InProgress: dbKanbanData.board.InProgress?.length || 0,
        Review: dbKanbanData.board.Review?.length || 0,
        Done: dbKanbanData.board.Done?.length || 0,
        Archived: dbKanbanData.board.Archived?.length || 0,
      })
      // Debug: Log story titles to verify data updates
      console.log('[KanbanBoard] Todo stories:', dbKanbanData.board.Todo?.map((s: any) => ({ id: s.id, title: s.title, story_code: s.story_code })))

      // Debug: Log all story types to identify filtering issues
      const allItems = [
        ...(dbKanbanData.board.Todo || []),
        ...(dbKanbanData.board.InProgress || []),
        ...(dbKanbanData.board.Review || []),
        ...(dbKanbanData.board.Done || []),
        ...(dbKanbanData.board.Archived || []),
      ]
      const uniqueTypes = [...new Set(allItems.map((item: any) => item.type))]
      console.log('[KanbanBoard] Story types in database:', uniqueTypes)

      // Lean Kanban: Only show UserStory and EnablerStory on board
      // Epic managed separately, Tasks are implementation details
      // FIX: Also include stories without type or with different casing
      const filterItems = (items: any[]) => {
        const filtered = items.filter((item: any) => {
          const itemType = item.type?.toLowerCase?.() || ''
          // Include items without type, or with UserStory/EnablerStory type (case-insensitive)
          return !item.type ||
            itemType === "userstory" ||
            itemType === "enablerstory"
        })
        console.log('[KanbanBoard] Filter result:', items.length, '->', filtered.length, 'items')
        return filtered
      }

      // TraDS ============= Kanban Hierarchy: Map items with parent/children relationships
      const mapItem = (item: any, columnId: string) => ({
        id: item.id,
        content: item.title,
        columnId,
        taskId: item.id,
        story_code: item.story_code,
        description: item.description,
        status: item.status,
        type: item.type,
        story_point: item.story_point,
        priority: item.priority,
        rank: item.rank,
        assignee_id: item.assignee_id,
        reviewer_id: item.reviewer_id,
        epic_id: item.epic_id,
        epic_code: item.epic_code,
        epic_title: item.epic_title,
        epic_description: item.epic_description,
        epic_domain: item.epic_domain,
        acceptance_criteria: item.acceptance_criteria,
        requirements: item.requirements,
        dependencies: item.dependencies,
        created_at: item.created_at,
        updated_at: item.updated_at,
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
          story_code: child.story_code,
          description: child.description,
          status: child.status,
          type: child.type,
          story_point: child.story_point,
          priority: child.priority,
          rank: child.rank,
          assignee_id: child.assignee_id,
          reviewer_id: child.reviewer_id,
          requirements: child.requirements,
          dependencies: child.dependencies,
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
        {
          id: "archived",
          title: "Archived",
          color: "border-gray-400",
          cards: filterItems(dbKanbanData.board.Archived || []).map((item: any) => mapItem(item, "archived")),
          wipLimit: undefined,
          limitType: undefined
        },
      ]

      console.log('[KanbanBoard] Setting new columns, Todo cards:', newColumns.find(c => c.id === 'todo')?.cards.map(c => ({ id: c.id, content: c.content })))
      setColumns(newColumns)
    }
  }, [dbKanbanData, dataUpdatedAt])  // Include dataUpdatedAt to force re-run on refetch

  // Update columns when WebSocket kanbanData changes (real-time updates)
  useEffect(() => {
    if (kanbanData && kanbanData.kanban_board) {
      console.log('[KanbanBoard] Updating Kanban board with WebSocket data:', kanbanData)

      // Lean Kanban: Only show UserStory and EnablerStory on board
      // Epic managed separately, Tasks are implementation details
      // FIX: Also include stories without type or with different casing
      const filterItems = (items: any[]) => {
        const filtered = items.filter((item: any) => {
          const itemType = item.type?.toLowerCase?.() || ''
          // Include items without type, or with UserStory/EnablerStory type (case-insensitive)
          return !item.type ||
            itemType === "userstory" ||
            itemType === "enablerstory"
        })
        return filtered
      }

      // TraDS ============= Kanban Hierarchy: Map items with parent/children relationships
      const mapItem = (item: any, columnId: string) => ({
        id: item.id,
        content: item.title,
        columnId,
        taskId: item.item_id || item.id,
        story_code: item.story_code,
        description: item.description,
        status: item.status,
        type: item.type,
        story_point: item.story_point,
        priority: item.priority,
        rank: item.rank,
        assignee_id: item.assignee_id,
        reviewer_id: item.reviewer_id,
        epic_id: item.epic_id,
        epic_code: item.epic_code,
        epic_title: item.epic_title,
        epic_description: item.epic_description,
        epic_domain: item.epic_domain,
        acceptance_criteria: item.acceptance_criteria,
        requirements: item.requirements,
        dependencies: item.dependencies,
        created_at: item.created_at,
        updated_at: item.updated_at,
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
          story_code: child.story_code,
          description: child.description,
          status: child.status,
          type: child.type,
          story_point: child.story_point,
          priority: child.priority,
          rank: child.rank,
          assignee_id: child.assignee_id,
          reviewer_id: child.reviewer_id,
          requirements: child.requirements,
          dependencies: child.dependencies,
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

  const handleDownloadResult = useCallback((card: KanbanCardData) => {
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
  }, [])

  const handleAddCard = useCallback((columnId: string, storyData: StoryFormData) => {
    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === columnId) {
          return {
            ...col,
            cards: [
              ...col.cards,
              {
                id: Date.now().toString(),
                content: storyData.title,
                description: storyData.description,
                columnId,
                type: storyData.type,
                story_point: storyData.story_point,
                rank: storyData.priority === "High" ? 1 : storyData.priority === "Medium" ? 5 : 9,
                taskId: `STORY-${Math.floor(Math.random() * 10000)}`,
              },
            ],
          }
        }
        return col
      }),
    )
  }, [])

  const handleCreateStory = useCallback(async (storyData: StoryFormData) => {
    console.log("handleCreateStory called with:", storyData, "projectId:", projectId)
    if (!projectId) {
      toast.error("Project ID is required to create a story")
      return
    }

    const toastId = toast.loading("Creating story...")
    try {
      // Call the API to create the story in the database
      console.log("About to create story via API:", { project_id: projectId, ...storyData })

      const createdStory = await storiesApi.create({
        project_id: projectId,
        title: storyData.title,
        description: storyData.description,
        story_type: storyData.type,
        story_point: storyData.story_point,
        priority: storyData.priority === "High" ? 1 : storyData.priority === "Medium" ? 2 : 3,
        acceptance_criteria: storyData.acceptance_criteria,
        requirements: storyData.requirements,
        dependencies: storyData.dependencies,
        epic_id: storyData.epic_id,
        tags: [],
        labels: [],
        // New epic fields (if creating new epic)
        new_epic_title: storyData.new_epic_title,
        new_epic_domain: storyData.new_epic_domain,
        new_epic_description: storyData.new_epic_description,
      })
      console.log("Story created successfully:", createdStory)

      // Add the created story to the frontend UI with all fields
      setColumns((prev) =>
        prev.map((col) => {
          if (col.id === "todo") {
            return {
              ...col,
              cards: [
                ...col.cards,
                {
                  id: createdStory.id,
                  content: createdStory.title,
                  description: createdStory.description || "",
                  columnId: "todo",
                  type: createdStory.type,
                  story_code: createdStory.story_code ?? undefined,
                  story_point: createdStory.story_point ?? undefined,
                  priority: createdStory.priority ?? undefined,
                  rank: createdStory.rank ?? undefined,
                  epic_id: createdStory.epic_id ?? undefined,
                  acceptance_criteria: createdStory.acceptance_criteria ?? undefined,
                  requirements: createdStory.requirements ?? undefined,
                  dependencies: createdStory.dependencies ?? undefined,
                  created_at: createdStory.created_at ?? new Date().toISOString(),
                },
              ],
            }
          }
          return col
        }),
      )

      toast.success("Story created successfully!")
    } catch (error) {
      console.error("Error creating story:", error)
      toast.error("Failed to create story. Please try again.")
    } finally {
      toast.dismiss(toastId)
    }
  }, [projectId])

  const handleUpdateStory = useCallback(async (storyId: string, storyData: StoryFormData) => {
    const toastId = toast.loading("Updating story...")
    try {
      const updatedStory = await storiesApi.update(storyId, {
        title: storyData.title,
        description: storyData.description,
        story_type: storyData.type,
        story_point: storyData.story_point,
        priority: storyData.priority === "High" ? 1 : storyData.priority === "Medium" ? 2 : 3,
        acceptance_criteria: storyData.acceptance_criteria,
        requirements: storyData.requirements,
        dependencies: storyData.dependencies,
        epic_id: storyData.epic_id,
      })

      // Update the story in UI with fresh data and new updated_at
      const now = new Date().toISOString()
      setColumns((prev) =>
        prev.map((col) => ({
          ...col,
          cards: col.cards.map((card) =>
            card.id === storyId
              ? {
                  ...card,
                  content: updatedStory.title,
                  description: updatedStory.description || "",
                  type: updatedStory.type,
                  story_point: updatedStory.story_point ?? storyData.story_point,
                  priority: updatedStory.priority ?? (storyData.priority === "High" ? 1 : storyData.priority === "Medium" ? 2 : 3),
                  // Update epic fields - convert null to undefined for type compatibility
                  epic_id: updatedStory.epic_id === null ? undefined : (updatedStory.epic_id ?? storyData.epic_id),
                  epic_code: updatedStory.epic_id ? (updatedStory.epic_code ?? card.epic_code) : undefined,
                  epic_title: updatedStory.epic_id ? (updatedStory.epic_title ?? card.epic_title) : undefined,
                  epic_description: updatedStory.epic_id ? (updatedStory.epic_description ?? card.epic_description) : undefined,
                  epic_domain: updatedStory.epic_id ? (updatedStory.epic_domain ?? card.epic_domain) : undefined,
                  acceptance_criteria: updatedStory.acceptance_criteria ?? storyData.acceptance_criteria,
                  requirements: updatedStory.requirements ?? storyData.requirements,
                  dependencies: updatedStory.dependencies ?? storyData.dependencies,
                  updated_at: updatedStory.updated_at ?? now,
                }
              : card
          ),
        }))
      )

      setEditingStory(null)
      toast.success("Story updated successfully!")
      
      // Refetch kanban data to get fresh epic info from backend
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['kanban-board', projectId] })
      }
    } catch (error) {
      console.error("Error updating story:", error)
      toast.error("Failed to update story. Please try again.")
    } finally {
      toast.dismiss(toastId)
    }
  }, [projectId, queryClient])

  const handleDeleteCard = useCallback(async (columnId: string, cardId: string) => {
    // Optimistic update - remove from UI immediately
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
    
    // Call API to delete from database
    try {
      console.log("[Kanban] Deleting story:", cardId)
      await storiesApi.delete(cardId)
      console.log("[Kanban] Delete success")
      toast.success("Đã xóa story")
    } catch (error) {
      console.error("[Kanban] Failed to delete story:", error)
      toast.error("Không thể xóa story")
      // Refetch to restore state on error
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['kanban-board', projectId] })
      }
    }
  }, [projectId, queryClient])

  const handleDuplicateCard = useCallback((cardId: string) => {
    setColumns((prev) =>
      prev.map((col) => {
        const cardIndex = col.cards.findIndex(c => c.id === cardId)
        if (cardIndex !== -1) {
          const originalCard = col.cards[cardIndex]
          const duplicatedCard: KanbanCardData = {
            ...originalCard,
            id: `${originalCard.id}-copy-${Date.now()}`,
            taskId: `${originalCard.taskId}-copy`,
            content: `${originalCard.content} (Copy)`,
          }
          return {
            ...col,
            cards: [...col.cards.slice(0, cardIndex + 1), duplicatedCard, ...col.cards.slice(cardIndex + 1)]
          }
        }
        return col
      })
    )
  }, [])

  const handleMoveCard = useCallback((cardId: string, targetColumnId: string) => {
    let cardToMove: KanbanCardData | null = null
    let sourceColumnId: string | null = null

    // Find the card and remove from source column
    setColumns((prev) => {
      const newColumns = prev.map((col) => {
        const cardIndex = col.cards.findIndex(c => c.id === cardId)
        if (cardIndex !== -1) {
          cardToMove = col.cards[cardIndex]
          sourceColumnId = col.id
          return {
            ...col,
            cards: col.cards.filter((card) => card.id !== cardId),
          }
        }
        return col
      })

      // Add to target column
      if (cardToMove) {
        return newColumns.map((col) => {
          if (col.id === targetColumnId) {
            return {
              ...col,
              cards: [...col.cards, { ...cardToMove!, columnId: targetColumnId }],
            }
          }
          return col
        })
      }
      return newColumns
    })
  }, [])

  const handleEditCard = useCallback((card: KanbanCardData) => {
    // Open the create/edit dialog with existing story data
    const storyType = card.type?.toLowerCase() === "enablerstory" ? "EnablerStory" : "UserStory"
    setEditingStory({
      id: card.id,
      title: card.content,
      description: card.description,
      type: storyType,
      story_point: card.story_point,
      priority: card.priority,
      rank: card.rank,
      acceptance_criteria: card.acceptance_criteria,
      requirements: card.requirements,
      dependencies: card.dependencies,
      epic_id: card.epic_id
    })
    setShowCreateStoryDialog(true)
  }, [])

  const handleDragStart = useCallback((card: KanbanCardData) => {
    setDraggedCard(card)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, columnId: string) => {
    e.preventDefault()
    setDraggedOverColumn(columnId)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDraggedOverColumn(null)
  }, [])

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
    console.log("Drag drop event:", {
      draggedCard,
      targetColumnId,
      projectId,
      oldStatus: draggedCard.columnId,
      newStatus: targetColumnId
    });

    if (projectId && draggedCard.id) {
      try {
        const statusMap: Record<string, 'Todo' | 'InProgress' | 'Review' | 'Done' | 'Archived'> = {
          'todo': 'Todo',
          'inprogress': 'InProgress',
          'review': 'Review',
          'done': 'Done',
          'archived': 'Archived',
        };

        const fromStatus = statusMap[draggedCard.columnId.toLowerCase()] || 'Todo';
        const toStatus = statusMap[targetColumnId.toLowerCase()] || 'Todo';

        console.log("About to validate policy move:", {
          projectId,
          storyId: draggedCard.id,
          fromStatus,
          toStatus
        });

        const policyValidation = await backlogItemsApi.validatePolicyMove(
          projectId,
          draggedCard.id, // Sử dụng UUID thật thay vì taskId tạm thời
          fromStatus,
          toStatus
        )

        console.log("Policy validation result:", policyValidation);

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

    // Also update the status on the backend via API
    try {
      const backendStatus = {
        'todo': 'Todo',
        'inprogress': 'InProgress',
        'review': 'Review',
        'done': 'Done',
        'archived': 'Archived',
      }[targetColumnId.toLowerCase()] || 'Todo';

      console.log("About to update story status via API:", {
        storyId: draggedCard.id,
        newStatus: backendStatus,
        targetColumnId: targetColumnId
      });

      // Import the stories API here if needed
      const { storiesApi } = await import('@/apis/stories');

      // Map column IDs to backend status format
      const statusMap: Record<string, 'Todo' | 'InProgress' | 'Review' | 'Done' | 'Archived'> = {
        'todo': 'Todo',
        'inprogress': 'InProgress',
        'review': 'Review',
        'done': 'Done',
        'archived': 'Archived',
      };

      await storiesApi.updateStatus(
        draggedCard.id,
        statusMap[targetColumnId.toLowerCase()] || 'Todo'
      );

      console.log("Successfully updated story status via API");
    } catch (error) {
      console.error("Failed to update story status via API:", error);
    }

    setDraggedCard(null)
    setDraggedOverColumn(null)
  }

  const handleDragEnd = useCallback(() => {
    setDraggedCard(null)
    setDraggedOverColumn(null)
  }, [])

  // Filter columns based on search query and filters
  const filteredColumns = useMemo(() => {
    return columns.map(column => {
      const filteredCards = column.cards.filter(card => {
        // Search filter
        const matchesSearch = !searchQuery ||
          card.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
          card.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          card.taskId?.toLowerCase().includes(searchQuery.toLowerCase())

        // Type filter
        const matchesType = selectedFilters.types.length === 0 ||
          (card.type && selectedFilters.types.includes(card.type))

        // Priority filter (based on rank)
        let matchesPriority = true
        if (selectedFilters.priorities.length > 0 && card.rank !== undefined && card.rank !== null) {
          matchesPriority = selectedFilters.priorities.some(priority => {
            if (priority === "high" && card.rank! <= 3) return true
            if (priority === "medium" && card.rank! > 3 && card.rank! <= 7) return true
            if (priority === "low" && card.rank! > 7) return true
            return false
          })
        } else if (selectedFilters.priorities.length > 0) {
          matchesPriority = false
        }

        return matchesSearch && matchesType && matchesPriority
      })

      return {
        ...column,
        cards: filteredCards
      }
    })
  }, [columns, searchQuery, selectedFilters])

  // Calculate active filter count for UI
  const activeFilterCount = selectedFilters.types.length + selectedFilters.priorities.length

  return (
    <>
      <div className="h-full bg-background flex flex-col">
        {/* Fixed Header with Settings Buttons - Modern & Minimal */}
        <div className="flex-shrink-0 flex flex-col gap-4 px-8 pt-6 pb-4 border-b border-border/40 bg-background">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground tracking-tight">Kanban Board</h2>
            {projectId && (
              <div className="flex gap-2.5">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => {
                    setEditingStory(null)
                    setShowCreateStoryDialog(true)
                  }}
                  className="gap-2 h-9 px-3.5 rounded-lg"
                >
                  <Plus className="w-4 h-4" />
                  <span className="font-medium">Create Story</span>
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 h-9 px-3.5 rounded-lg hover:bg-muted/80 transition-colors"
                    >
                      <BarChart3 className="w-4 h-4" />
                      <span className="font-medium">Analytics</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => setShowCFD(true)}>
                      <TrendingUp className="w-4 h-4 mr-2" />
                      CFD
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setShowFlowMetrics(true)}>
                      <Activity className="w-4 h-4 mr-2" />
                      Metrics
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setShowPolicySettings(true)}>
                      <Settings className="w-4 h-4 mr-2" />
                      WIP Limits
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>

          {/* Search and Filter Bar */}
          <div className="flex gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search cards..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-10 h-9 rounded-lg bg-muted/30 border-border/50 focus:bg-background transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <Button
              variant={activeFilterCount > 0 ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="gap-2 h-9 px-3.5 rounded-lg"
            >
              <Filter className="w-4 h-4" />
              <span className="font-medium">
                Filters
                {activeFilterCount > 0 && ` (${activeFilterCount})`}
              </span>
            </Button>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-4">
              {/* Type Filter - Lean Kanban: Only UserStory and EnablerStory */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-foreground">Type</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: "UserStory", label: "User Story" },
                    { value: "EnablerStory", label: "Enabler Story" }
                  ].map((type) => (
                    <button
                      key={type.value}
                      onClick={() => {
                        setSelectedFilters(prev => ({
                          ...prev,
                          types: prev.types.includes(type.value)
                            ? prev.types.filter(t => t !== type.value)
                            : [...prev.types, type.value]
                        }))
                      }}
                      className={`
                        px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
                        ${selectedFilters.types.includes(type.value)
                          ? "bg-primary text-primary-foreground"
                          : "bg-background border border-border/50 hover:bg-muted"
                        }
                      `}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Priority Filter */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-foreground">Priority</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: "high", label: "High (1-3)" },
                    { value: "medium", label: "Medium (4-7)" },
                    { value: "low", label: "Low (8+)" }
                  ].map((priority) => (
                    <button
                      key={priority.value}
                      onClick={() => {
                        setSelectedFilters(prev => ({
                          ...prev,
                          priorities: prev.priorities.includes(priority.value)
                            ? prev.priorities.filter(p => p !== priority.value)
                            : [...prev.priorities, priority.value]
                        }))
                      }}
                      className={`
                        px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
                        ${selectedFilters.priorities.includes(priority.value)
                          ? "bg-primary text-primary-foreground"
                          : "bg-background border border-border/50 hover:bg-muted"
                        }
                      `}
                    >
                      {priority.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Clear Filters */}
              {activeFilterCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFilters({ types: [], priorities: [] })}
                  className="w-full h-8"
                >
                  Clear All Filters
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Scrollable Content Area */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-x-auto overflow-y-auto"
          style={{ scrollBehavior: "smooth" }}
        >
          {/* Lean Kanban Alerts - Better spacing */}
          {projectId && flowMetrics && (
            <div className="px-8 pt-4 space-y-3">
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

          {/* Columns - Better spacing and layout */}
          <div className="flex gap-6 min-w-max px-8 py-6">
            {filteredColumns.map((column) => (
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
                onCardDuplicate={handleDuplicateCard}
                onCardMove={handleMoveCard}
                onCardEdit={handleEditCard}
              />
            ))}
          </div>
        </div>
      </div>

      <TaskDetailModal
        card={selectedCard}
        open={!!selectedCard}
        onOpenChange={() => setSelectedCard(null)}
        onDownloadResult={handleDownloadResult}
        allStories={columns.flatMap(col => col.cards)}
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

      <CreateStoryDialog
        open={showCreateStoryDialog}
        onOpenChange={(open) => {
          setShowCreateStoryDialog(open)
          if (!open) setEditingStory(null)
        }}
        onCreateStory={handleCreateStory}
        onUpdateStory={handleUpdateStory}
        projectId={projectId}
        editingStory={editingStory}
      />
    </>
  )
}
