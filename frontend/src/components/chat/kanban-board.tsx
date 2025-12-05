import type React from "react"
import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Settings, Activity, TrendingUp, Search, Filter, X, Plus, BarChart3 } from "lucide-react"
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TaskDetailModal } from "./task-detail-modal"
import { FlowMetricsDashboard } from "./flow-metrics-dashboard"
import { PolicyValidationDialog, type PolicyViolation } from "./policy-validation-dialog"
import { PolicySettingsDialog } from "./policy-settings-dialog"
import { AgingItemsAlert } from "./aging-items-alert"
import { BottleneckAlert } from "./bottleneck-alert"
import { CumulativeFlowDiagram } from "./cumulative-flow-diagram"
import { KanbanCard, type KanbanCardData } from "./kanban-card"
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

type ColumnId = "todo" | "inprogress" | "review" | "done" | "archived"

interface Column {
  id: ColumnId
  title: string
  wipLimit?: number
  limitType?: 'hard' | 'soft'
}

const COLUMNS: Column[] = [
  { id: "todo", title: "ToDo" },
  { id: "inprogress", title: "InProgress", wipLimit: 5, limitType: "soft" },
  { id: "review", title: "Review", wipLimit: 3, limitType: "soft" },
  { id: "done", title: "Done" },
  { id: "archived", title: "Archived" },
]

// Sortable Card Component
function SortableCard({
  card,
  onCardClick,
  onCardDelete,
  onCardDownloadResult,
  onCardDuplicate,
  onCardMove,
  onCardEdit,
}: {
  card: KanbanCardData
  onCardClick: (card: KanbanCardData) => void
  onCardDelete: (cardId: string) => void
  onCardDownloadResult: (card: KanbanCardData) => void
  onCardDuplicate?: (cardId: string) => void
  onCardMove?: (cardId: string, targetColumn: string) => void
  onCardEdit?: (card: KanbanCardData) => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <KanbanCard
        card={card}
        isDragging={isDragging}
        onDragStart={() => {}}
        onDragEnd={() => {}}
        onClick={() => onCardClick(card)}
        onDelete={() => onCardDelete(card.id)}
        onDownloadResult={() => onCardDownloadResult(card)}
        onDuplicate={onCardDuplicate ? () => onCardDuplicate(card.id) : undefined}
        onMove={onCardMove ? (targetColumn) => onCardMove(card.id, targetColumn) : undefined}
        onEdit={onCardEdit ? () => onCardEdit(card) : undefined}
      />
    </div>
  )
}

// Droppable Column Component
function DroppableColumn({
  column,
  cards,
  wipData,
  onCardClick,
  onCardDelete,
  onCardDownloadResult,
  onCardDuplicate,
  onCardMove,
  onCardEdit,
}: {
  column: Column
  cards: KanbanCardData[]
  wipData?: { wip_limit?: number; limit_type?: string }
  onCardClick: (card: KanbanCardData) => void
  onCardDelete: (cardId: string) => void
  onCardDownloadResult: (card: KanbanCardData) => void
  onCardDuplicate?: (cardId: string) => void
  onCardMove?: (cardId: string, targetColumn: string) => void
  onCardEdit?: (card: KanbanCardData) => void
}) {
  // Make the column itself droppable ONLY for empty columns
  // When column has cards, only cards are droppables to ensure accurate positioning
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    disabled: cards.length > 0, // Disable column droppable when it has cards
  })

  const wipLimit = wipData?.wip_limit ?? column.wipLimit
  const limitType = wipData?.limit_type ?? column.limitType

  const getWIPBadgeStyle = () => {
    if (!wipLimit) return "bg-slate-100 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300 font-medium"
    const utilization = cards.length / wipLimit
    if (cards.length >= wipLimit) {
      return "bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 font-semibold border border-red-200/50"
    } else if (utilization >= 0.8) {
      return "bg-orange-50 dark:bg-orange-950/50 text-orange-700 dark:text-orange-300 font-medium border border-orange-200/50"
    }
    return "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200/50"
  }

  return (
    <div className="w-72 flex-shrink-0">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border/40">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-foreground tracking-tight">{column.title}</h3>
          <span className={`text-xs px-2.5 py-1 rounded-lg ${getWIPBadgeStyle()}`}>
            {column.id === "todo" || column.id === "archived"
              ? cards.length
              : wipLimit
                ? `${cards.length}/${wipLimit}`
                : cards.length}
          </span>
        </div>
        {wipLimit && cards.length >= wipLimit && column.id !== "todo" && (
          <span className="text-sm" title="WIP limit reached">🚫</span>
        )}
      </div>

      <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
        <div 
          ref={cards.length === 0 ? setNodeRef : undefined}
          className={`space-y-3 min-h-[100px] rounded-xl p-3 border-2 transition-colors ${
            isOver && cards.length === 0 ? "border-dashed border-primary bg-primary/5" : "border-transparent"
          }`}
        >
          {cards.map((card) => (
            <SortableCard
              key={card.id}
              card={card}
              onCardClick={onCardClick}
              onCardDelete={onCardDelete}
              onCardDownloadResult={onCardDownloadResult}
              onCardDuplicate={onCardDuplicate}
              onCardMove={onCardMove}
              onCardEdit={onCardEdit}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}

export function KanbanBoard({ kanbanData, projectId }: KanbanBoardProps) {
  const [cards, setCards] = useState<KanbanCardData[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [clonedCards, setClonedCards] = useState<KanbanCardData[] | null>(null)
  const recentlyMovedToNewContainer = useRef(false)
  const lastOverId = useRef<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<KanbanCardData | null>(null)
  const [showFlowMetrics, setShowFlowMetrics] = useState(false)
  const [showPolicySettings, setShowPolicySettings] = useState(false)
  const [showCFD, setShowCFD] = useState(false)
  const [showCreateStoryDialog, setShowCreateStoryDialog] = useState(false)
  const [editingStory, setEditingStory] = useState<StoryEditData | null>(null)
  const [policyViolation, setPolicyViolation] = useState<PolicyViolation | null>(null)
  const [flowMetrics, setFlowMetrics] = useState<any>(null)
  const [wipLimits, setWipLimits] = useState<Record<string, any>>({})
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Search and Filter state
  const [searchQuery, setSearchQuery] = useState("")
  const [showFilters, setShowFilters] = useState(false)
  const [selectedFilters, setSelectedFilters] = useState<{ types: string[]; priorities: string[] }>({
    types: [],
    priorities: [],
  })

  const { data: dbKanbanData, isLoading, dataUpdatedAt } = useKanbanBoard(projectId)
  const queryClient = useQueryClient()

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // Load flow metrics - disabled auto-load, only load when user opens metrics dashboard
  // useEffect(() => {
  //   if (projectId) {
  //     loadFlowMetrics()
  //     const interval = setInterval(loadFlowMetrics, 5 * 60 * 1000)
  //     return () => clearInterval(interval)
  //   }
  // }, [projectId])

  const loadFlowMetrics = async () => {
    if (!projectId) return
    try {
      const metrics = await backlogItemsApi.getFlowMetrics(projectId, 30)
      setFlowMetrics(metrics)
    } catch (error) {
      console.error('Failed to load flow metrics:', error)
    }
  }

  // Load data from database
  useEffect(() => {
    if (dbKanbanData && dbKanbanData.board) {
      const filterItems = (items: any[]) =>
        items.filter((item: any) => {
          const itemType = item.type?.toLowerCase?.() || ''
          return !item.type || itemType === "userstory" || itemType === "enablerstory"
        })

      const mapItem = (item: any, columnId: string): KanbanCardData => ({
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
      })

      const allCards: KanbanCardData[] = [
        ...filterItems(dbKanbanData.board.Todo || []).map((item: any) => mapItem(item, "todo")),
        ...filterItems(dbKanbanData.board.InProgress || []).map((item: any) => mapItem(item, "inprogress")),
        ...filterItems(dbKanbanData.board.Review || []).map((item: any) => mapItem(item, "review")),
        ...filterItems(dbKanbanData.board.Done || []).map((item: any) => mapItem(item, "done")),
        ...filterItems(dbKanbanData.board.Archived || []).map((item: any) => mapItem(item, "archived")),
      ]

      setCards(allCards)
      setWipLimits(dbKanbanData.wip_limits || {})
    }
  }, [dbKanbanData, dataUpdatedAt])

  // Derive the current selected card data from cards (instead of syncing via useEffect)
  const currentSelectedCard = useMemo(() => {
    if (!selectedCard) return null
    return cards.find(c => c.id === selectedCard.id) || selectedCard
  }, [cards, selectedCard?.id])

  // Get the active card for DragOverlay
  const activeCard = useMemo(() => {
    if (!activeId) return null
    return cards.find(c => c.id === activeId) || null
  }, [activeId, cards])

  // Reset recentlyMovedToNewContainer after layout settles (official dnd-kit pattern)
  useEffect(() => {
    requestAnimationFrame(() => {
      recentlyMovedToNewContainer.current = false
    })
  }, [cards])

  // Get cards by column
  const getCardsByColumn = useCallback((columnId: string) => {
    return cards
      .filter(card => card.columnId === columnId)
      .sort((a, b) => (a.rank || 999) - (b.rank || 999))
  }, [cards])

  // Filter cards
  const filterCards = useCallback((cardsToFilter: KanbanCardData[]) => {
    return cardsToFilter.filter(card => {
      const matchesSearch = !searchQuery ||
        card.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        card.description?.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesType = selectedFilters.types.length === 0 ||
        (card.type && selectedFilters.types.includes(card.type))

      let matchesPriority = true
      if (selectedFilters.priorities.length > 0 && card.rank !== undefined) {
        matchesPriority = selectedFilters.priorities.some(priority => {
          if (priority === "high" && card.rank! <= 3) return true
          if (priority === "medium" && card.rank! > 3 && card.rank! <= 7) return true
          if (priority === "low" && card.rank! > 7) return true
          return false
        })
      }

      return matchesSearch && matchesType && matchesPriority
    })
  }, [searchQuery, selectedFilters])

  // Find container for an item (official dnd-kit pattern)
  const findContainer = useCallback((id: string): string | undefined => {
    // Check if id is a column
    if (COLUMNS.some(col => col.id === id)) {
      return id
    }
    // Find the column containing this card
    const card = cards.find(c => c.id === id)
    return card?.columnId
  }, [cards])

  // DnD Handlers (following official dnd-kit pattern)
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string)
    setClonedCards(cards) // Save for cancel recovery
  }, [cards])

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event
    const overId = over?.id as string | undefined

    if (overId == null) return

    const overContainer = findContainer(overId)
    const activeContainer = findContainer(active.id as string)

    if (!overContainer || !activeContainer || activeContainer === overContainer) {
      return
    }

    // Moving to different container
    setCards(prevCards => {
      const activeItems = prevCards.filter(c => c.columnId === activeContainer)
      const overItems = prevCards.filter(c => c.columnId === overContainer)
      
      // Find indices
      const activeIndex = activeItems.findIndex(c => c.id === active.id)
      const overIndex = overItems.findIndex(c => c.id === overId)

      let newIndex: number
      if (COLUMNS.some(col => col.id === overId)) {
        // Dropping on container itself - add to end
        newIndex = overItems.length
      } else {
        // Dropping on an item - calculate position
        const isBelowOverItem = over && 
          active.rect.current.translated &&
          active.rect.current.translated.top > over.rect.top + over.rect.height

        const modifier = isBelowOverItem ? 1 : 0
        newIndex = overIndex >= 0 ? overIndex + modifier : overItems.length
      }

      recentlyMovedToNewContainer.current = true

      // Update cards: change columnId and recalculate ranks
      const activeCard = prevCards.find(c => c.id === active.id)
      if (!activeCard) return prevCards

      // Remove from old container, add to new container at correct position
      const newCards = prevCards.filter(c => c.id !== active.id)
      
      // Get current items in target container and insert at newIndex
      const targetItems = newCards
        .filter(c => c.columnId === overContainer)
        .sort((a, b) => (a.rank || 999) - (b.rank || 999))
      
      // Calculate new ranks for target container
      const updatedCards = newCards.map(card => {
        if (card.columnId === overContainer) {
          const currentIndex = targetItems.findIndex(c => c.id === card.id)
          const adjustedIndex = currentIndex >= newIndex ? currentIndex + 1 : currentIndex
          return { ...card, rank: adjustedIndex + 1 }
        }
        return card
      })

      // Add the moved card with new columnId and rank
      updatedCards.push({
        ...activeCard,
        columnId: overContainer,
        rank: newIndex + 1
      })

      return updatedCards
    })
  }, [findContainer])

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event
    const originalColumnId = clonedCards?.find(c => c.id === active.id)?.columnId

    // Always reset active state
    setActiveId(null)
    setClonedCards(null)

    if (!over) return

    const overId = over.id as string
    const activeContainer = findContainer(active.id as string)
    const overContainer = findContainer(overId)

    if (!activeContainer || !overContainer) return

    const statusMap: Record<string, 'Todo' | 'InProgress' | 'Review' | 'Done' | 'Archived'> = {
      'todo': 'Todo',
      'inprogress': 'InProgress',
      'review': 'Review', 
      'done': 'Done',
      'archived': 'Archived',
    }

    // Same container - handle reordering with arrayMove (official pattern)
    if (activeContainer === overContainer) {
      const containerCards = cards
        .filter(c => c.columnId === activeContainer)
        .sort((a, b) => (a.rank || 999) - (b.rank || 999))

      const activeIndex = containerCards.findIndex(c => c.id === active.id)
      const overIndex = containerCards.findIndex(c => c.id === overId)

      if (activeIndex !== overIndex && activeIndex !== -1 && overIndex !== -1) {
        const reorderedCards = arrayMove(containerCards, activeIndex, overIndex)
        
        // Update ranks
        const newRanks = new Map<string, number>()
        reorderedCards.forEach((card, index) => {
          newRanks.set(card.id, index + 1)
        })

        setCards(prev => prev.map(card => {
          const newRank = newRanks.get(card.id)
          return newRank !== undefined ? { ...card, rank: newRank } : card
        }))

        // Save to backend
        if (projectId) {
          try {
            const rankUpdates: { story_id: string; rank: number }[] = []
            newRanks.forEach((rank, cardId) => rankUpdates.push({ story_id: cardId, rank }))
            await storiesApi.bulkUpdateRanks(rankUpdates)
            toast.success("Đã cập nhật thứ tự")
          } catch (error) {
            console.error("Failed to update rank:", error)
            toast.error("Không thể cập nhật thứ tự")
          }
        }
      }
    } else {
      // Cross-container move - handleDragOver already updated state
      // Just need to save to backend
      const currentCard = cards.find(c => c.id === active.id)
      if (!currentCard || !originalColumnId) return

      // Get all cards in the new container for rank update
      const containerCards = cards
        .filter(c => c.columnId === overContainer)
        .sort((a, b) => (a.rank || 999) - (b.rank || 999))

      const newRanks = new Map<string, number>()
      containerCards.forEach((card, index) => {
        newRanks.set(card.id, index + 1)
      })

      // Save to backend
      try {
        await storiesApi.updateStatus(active.id as string, statusMap[overContainer] || 'Todo')
        
        const rankUpdates: { story_id: string; rank: number }[] = []
        newRanks.forEach((rank, cardId) => rankUpdates.push({ story_id: cardId, rank }))
        if (rankUpdates.length > 0) {
          await storiesApi.bulkUpdateRanks(rankUpdates)
        }
        toast.success("Đã cập nhật trạng thái story")
      } catch (error) {
        console.error("Failed to update status:", error)
        toast.error("Không thể cập nhật trạng thái")
        // Revert to original state on error
        if (clonedCards) {
          setCards(clonedCards)
        }
      }
    }
  }, [cards, clonedCards, findContainer, projectId])

  // Handle drag cancel - restore original state
  const handleDragCancel = useCallback(() => {
    if (clonedCards) {
      setCards(clonedCards)
    }
    setActiveId(null)
    setClonedCards(null)
  }, [clonedCards])

  // Card handlers
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

  const handleCreateStory = useCallback(async (storyData: StoryFormData) => {
    if (!projectId) {
      toast.error("Project ID is required")
      return
    }
    const toastId = toast.loading("Creating story...")
    try {
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
        new_epic_title: storyData.new_epic_title,
        new_epic_domain: storyData.new_epic_domain,
        new_epic_description: storyData.new_epic_description,
      })

      setCards(prev => [...prev, {
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
      }])
      toast.success("Story created successfully!")
    } catch (error) {
      console.error("Error creating story:", error)
      toast.error("Failed to create story")
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

      const now = new Date().toISOString()
      setCards(prev => prev.map(card =>
        card.id === storyId
          ? {
              ...card,
              content: updatedStory.title,
              description: updatedStory.description || "",
              type: updatedStory.type,
              story_point: updatedStory.story_point ?? storyData.story_point,
              priority: updatedStory.priority ?? (storyData.priority === "High" ? 1 : storyData.priority === "Medium" ? 2 : 3),
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
      ))

      setEditingStory(null)
      toast.success("Story updated successfully!")

      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['kanban-board', projectId] })
      }
    } catch (error) {
      console.error("Error updating story:", error)
      toast.error("Failed to update story")
    } finally {
      toast.dismiss(toastId)
    }
  }, [projectId, queryClient])

  const handleDeleteCard = useCallback(async (cardId: string) => {
    setCards(prev => prev.filter(card => card.id !== cardId))
    try {
      await storiesApi.delete(cardId)
      toast.success("Đã xóa story")
    } catch (error) {
      console.error("Failed to delete story:", error)
      toast.error("Không thể xóa story")
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['kanban-board', projectId] })
      }
    }
  }, [projectId, queryClient])

  const handleDuplicateCard = useCallback((cardId: string) => {
    const card = cards.find(c => c.id === cardId)
    if (card) {
      setCards(prev => [...prev, {
        ...card,
        id: `${card.id}-copy-${Date.now()}`,
        content: `${card.content} (Copy)`,
      }])
    }
  }, [cards])

  const handleMoveCard = useCallback(async (cardId: string, targetColumnId: string) => {
    const card = cards.find(c => c.id === cardId)
    if (!card || card.columnId === targetColumnId) return

    setCards(prev => prev.map(c =>
      c.id === cardId ? { ...c, columnId: targetColumnId } : c
    ))

    try {
      const statusMap: Record<string, 'Todo' | 'InProgress' | 'Review' | 'Done' | 'Archived'> = {
        'todo': 'Todo',
        'inprogress': 'InProgress',
        'review': 'Review',
        'done': 'Done',
        'archived': 'Archived',
      }
      await storiesApi.updateStatus(cardId, statusMap[targetColumnId] || 'Todo')
    } catch (error) {
      console.error("Failed to move card:", error)
      setCards(prev => prev.map(c =>
        c.id === cardId ? { ...c, columnId: card.columnId } : c
      ))
    }
  }, [cards])

  const handleEditCard = useCallback((card: KanbanCardData) => {
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
      epic_id: card.epic_id,
    })
    setShowCreateStoryDialog(true)
  }, [])

  const activeFilterCount = selectedFilters.types.length + selectedFilters.priorities.length

  return (
    <>
      <div className="h-full bg-background flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 flex flex-col gap-4 px-8 pt-6 pb-4 border-b border-border/40 bg-background">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground tracking-tight">Kanban Board</h2>
            {projectId && (
              <div className="flex gap-2.5">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => { setEditingStory(null); setShowCreateStoryDialog(true) }}
                  className="gap-2 h-9 px-3.5 rounded-lg"
                >
                  <Plus className="w-4 h-4" />
                  <span className="font-medium">Create Story</span>
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-2 h-9 px-3.5 rounded-lg">
                      <BarChart3 className="w-4 h-4" />
                      <span className="font-medium">Analytics</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => setShowCFD(true)}>
                      <TrendingUp className="w-4 h-4 mr-2" /> CFD
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setShowFlowMetrics(true)}>
                      <Activity className="w-4 h-4 mr-2" /> Metrics
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setShowPolicySettings(true)}>
                      <Settings className="w-4 h-4 mr-2" /> WIP Limits
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>

          {/* Search and Filter */}
          <div className="flex gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search cards..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-10 h-9 rounded-lg bg-muted/30"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 transform -translate-y-1/2">
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
              Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
            </Button>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-semibold">Type</label>
                <div className="flex flex-wrap gap-2">
                  {[{ value: "UserStory", label: "User Story" }, { value: "EnablerStory", label: "Enabler Story" }].map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setSelectedFilters(prev => ({
                        ...prev,
                        types: prev.types.includes(type.value)
                          ? prev.types.filter(t => t !== type.value)
                          : [...prev.types, type.value]
                      }))}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        selectedFilters.types.includes(type.value)
                          ? "bg-primary text-primary-foreground"
                          : "bg-background border border-border/50 hover:bg-muted"
                      }`}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>
              {activeFilterCount > 0 && (
                <Button variant="ghost" size="sm" onClick={() => setSelectedFilters({ types: [], priorities: [] })} className="w-full h-8">
                  Clear All Filters
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Kanban Board with DnD */}
        <div ref={scrollContainerRef} className="flex-1 overflow-x-auto overflow-y-auto" style={{ scrollBehavior: "smooth" }}>
          {projectId && flowMetrics && (
            <div className="px-8 pt-4 space-y-3">
              <AgingItemsAlert
                projectId={projectId}
                agingItems={flowMetrics.aging_items || []}
                onCardClick={(itemId) => {
                  const card = cards.find(c => c.taskId === itemId || c.id === itemId)
                  if (card) setSelectedCard(card)
                }}
              />
              <BottleneckAlert bottlenecks={flowMetrics.bottlenecks || {}} threshold={48} />
            </div>
          )}

          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
          >
            <div className="flex gap-6 min-w-max px-8 py-6">
              {COLUMNS.map((column) => (
                <DroppableColumn
                  key={column.id}
                  column={column}
                  cards={filterCards(getCardsByColumn(column.id))}
                  wipData={wipLimits[column.title]}
                  onCardClick={setSelectedCard}
                  onCardDelete={handleDeleteCard}
                  onCardDownloadResult={handleDownloadResult}
                  onCardDuplicate={handleDuplicateCard}
                  onCardMove={handleMoveCard}
                  onCardEdit={handleEditCard}
                />
              ))}
            </div>

            <DragOverlay>
              {activeCard && (
                <div className="rotate-3 opacity-90">
                  <KanbanCard
                    card={activeCard}
                    isDragging={true}
                    onDragStart={() => {}}
                    onDragEnd={() => {}}
                    onClick={() => {}}
                    onDelete={() => {}}
                    onDownloadResult={() => {}}
                  />
                </div>
              )}
            </DragOverlay>
          </DndContext>
        </div>
      </div>

      <TaskDetailModal
        card={currentSelectedCard}
        open={!!currentSelectedCard}
        onOpenChange={() => setSelectedCard(null)}
        onDownloadResult={handleDownloadResult}
        allStories={cards}
      />

      <FlowMetricsDashboard projectId={projectId} open={showFlowMetrics} onOpenChange={setShowFlowMetrics} />
      <PolicyValidationDialog violation={policyViolation} cardTitle={activeCard?.content} open={!!policyViolation} onOpenChange={(open) => !open && setPolicyViolation(null)} />
      <PolicySettingsDialog projectId={projectId} open={showPolicySettings} onOpenChange={setShowPolicySettings} />
      <CumulativeFlowDiagram projectId={projectId} open={showCFD} onOpenChange={setShowCFD} />

      <CreateStoryDialog
        open={showCreateStoryDialog}
        onOpenChange={(open) => { setShowCreateStoryDialog(open); if (!open) setEditingStory(null) }}
        onCreateStory={handleCreateStory}
        onUpdateStory={handleUpdateStory}
        projectId={projectId}
        editingStory={editingStory}
      />
    </>
  )
}
