import type React from "react"
import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Search, Filter, X, Plus } from "lucide-react"
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

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TaskDetailModal } from "./task-detail-modal"
import { KanbanCard, type KanbanCardData } from "./kanban-card"
import { CreateStoryDialog, type StoryFormData, type StoryEditData } from "./create-story-dialog"
import { useKanbanBoard } from "@/queries/backlog-items"
import { storiesApi } from "@/apis/stories"
import { toast } from "@/lib/toast"
import { useQueryClient } from "@tanstack/react-query"

interface KanbanBoardProps {
  kanbanData?: any
  projectId?: string
  onViewFiles?: (worktreePath: string) => void
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
  // Only allow drag when agent_state is null, finished, or canceled
  const canDrag = !card.agent_state || card.agent_state === 'FINISHED' || card.agent_state === 'CANCELED'
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ 
    id: card.id,
    disabled: !canDrag  // Disable drag when agent is pending/processing
  })

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

export function KanbanBoard({ kanbanData, projectId, onViewFiles }: KanbanBoardProps) {
  const [cards, setCards] = useState<KanbanCardData[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [clonedCards, setClonedCards] = useState<KanbanCardData[] | null>(null)
  const clonedCardsRef = useRef<KanbanCardData[] | null>(null) // Ref version for callbacks
  const cardsRef = useRef<KanbanCardData[]>(cards) // Current cards ref for callbacks
  const activeCardRef = useRef<KanbanCardData | null>(null) // Store active card on drag start to avoid recalc
  // Store target position for cross-container moves
  const crossContainerTarget = useRef<{ targetColumn: string; targetIndex: number; overId: string } | null>(null)
  // Track last updated container to prevent redundant updates
  const lastOverContainerRef = useRef<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<KanbanCardData | null>(null)
  const [showCreateStoryDialog, setShowCreateStoryDialog] = useState(false)
  const [editingStory, setEditingStory] = useState<StoryEditData | null>(null)
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
        dependencies: item.dependencies || [],
        created_at: item.created_at,
        updated_at: item.updated_at,
        agent_state: item.agent_state,
        running_port: item.running_port,
        running_pid: item.running_pid,
        worktree_path: item.worktree_path,
        worktree_path_display: item.worktree_path_display,
        branch_name: item.branch_name,
        pr_url: item.pr_url,
        merge_status: item.merge_status,
        started_at: item.started_at,
        // Use pre-computed blocked state from backend (O(1) instead of frontend O(n²))
        isBlocked: item.is_blocked ?? false,
        blockedByCount: item.blocked_by_count ?? 0,
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

  // Get the active card for DragOverlay - use ref to avoid recalc on every cards change
  const activeCard = activeId ? activeCardRef.current : null

  // Keep cardsRef in sync with cards state
  useEffect(() => {
    cardsRef.current = cards
  }, [cards])

  // Listen for story state changes from WebSocket
  useEffect(() => {
    const handleStoryStateChanged = (event: CustomEvent) => {
      const { story_id, agent_state, sub_status, running_port, running_pid, pr_state, merge_status } = event.detail
      
      setCards(prev => {
        const updatedCards = prev.map(card => {
          if (card.id !== story_id) return card
          const updated = { ...card }
          if (agent_state !== undefined) updated.agent_state = agent_state
          if (sub_status !== undefined) updated.agent_sub_status = sub_status
          if (agent_state && agent_state !== 'PENDING') updated.agent_sub_status = null
          if (running_port !== undefined) updated.running_port = running_port
          if (running_pid !== undefined) updated.running_pid = running_pid
          if (pr_state !== undefined) updated.pr_state = pr_state
          if (merge_status !== undefined) updated.merge_status = merge_status
          return updated
        })
        return updatedCards
      })
    }
    
    window.addEventListener('story-state-changed', handleStoryStateChanged as EventListener)
    return () => {
      window.removeEventListener('story-state-changed', handleStoryStateChanged as EventListener)
    }
  }, [])

  // Listen for story status changes (e.g., moved to Done after merge)
  useEffect(() => {
    const handleStoryStatusChanged = (event: CustomEvent) => {
      const { story_id, status, merge_status, pr_state } = event.detail
      
      setCards(prev => {
        const updatedCards = prev.map(card => {
          if (card.id !== story_id) return card
          const updated = { ...card }
          if (status) updated.columnId = status.toLowerCase()
          if (merge_status !== undefined) updated.merge_status = merge_status
          if (pr_state !== undefined) updated.pr_state = pr_state
          return updated
        })
        return updatedCards
      })
    }
    
    window.addEventListener('story-status-changed', handleStoryStatusChanged as EventListener)
    return () => {
      window.removeEventListener('story-status-changed', handleStoryStatusChanged as EventListener)
    }
  }, [])

  // Get cards by column
  const getCardsByColumn = useCallback((columnId: string) => {
    return cards
      .filter(card => card.columnId === columnId)
      .sort((a, b) => (a.rank || 999) - (b.rank || 999))
  }, [cards])

  // Check if card has incomplete dependencies (blocked state)
  // Cards in Done or Archived columns are never shown as blocked
  // Optional cardsSource parameter to use original cards during drag operations
  const checkDependenciesCompleted = useCallback((card: KanbanCardData, cardsSource?: KanbanCardData[]): { 
    isBlocked: boolean
    incompleteDeps: KanbanCardData[]
    blockedByCount: number
  } => {
    const sourceCards = cardsSource || cards
    
    // Don't show blocked state for cards already in Done or Archived
    if (!card.dependencies?.length || card.columnId === 'done' || card.columnId === 'archived') {
      return { isBlocked: false, incompleteDeps: [], blockedByCount: 0 }
    }
    
    const incompleteDeps = card.dependencies
      .map(depId => sourceCards.find(c => c.id === depId))
      .filter((dep): dep is KanbanCardData => 
        dep !== undefined && dep.columnId !== 'done' && dep.columnId !== 'archived'
      )
    
    return { 
      isBlocked: incompleteDeps.length > 0, 
      incompleteDeps,
      blockedByCount: incompleteDeps.length
    }
  }, [cards])

  // Filter cards - blocked state is now pre-computed from backend
  const filterCards = useCallback((cardsToFilter: KanbanCardData[]) => {
    return cardsToFilter
      .filter(card => {
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
    // No need to enrich with blocked state - it's pre-computed from backend
  }, [searchQuery, selectedFilters])

  // Find container for an item (official dnd-kit pattern)
  // FIX: Use cardsRef instead of cards dependency to prevent infinite loop
  const findContainer = useCallback((id: string): string | undefined => {
    // Check if id is a column
    if (COLUMNS.some(col => col.id === id)) {
      return id
    }
    // Find the column containing this card using ref (avoids dependency on cards state)
    const card = cardsRef.current.find(c => c.id === id)
    return card?.columnId
  }, [])

  // DnD Handlers (following official dnd-kit pattern)
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const dragId = event.active.id as string
    setActiveId(dragId)
    setClonedCards(cards) // Save for cancel recovery
    clonedCardsRef.current = cards // Also save to ref for callbacks
    activeCardRef.current = cards.find(c => c.id === dragId) || null // Store active card to avoid recalc
    crossContainerTarget.current = null // Clear any stale target
    lastOverContainerRef.current = null // Reset last container tracking
  }, [cards])

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event
    const overId = over?.id as string | undefined

    if (overId == null) return

    const overContainer = findContainer(overId)
    const originalColumn = clonedCardsRef.current?.find(c => c.id === active.id)?.columnId

    if (!overContainer || !originalColumn) return

    // Check if this is a cross-container move
    const isCrossContainerMove = originalColumn !== overContainer

    if (!isCrossContainerMove) {
      crossContainerTarget.current = null
      lastOverContainerRef.current = null
      return
    }

    // Skip update if hovering over self (active card)
    if (overId === active.id) {
      return
    }

    // FIX INFINITE LOOP: Skip update if we're still hovering over the same container
    // This prevents redundant setCards calls when dragging within same target container
    if (lastOverContainerRef.current === overContainer) {
      // Just update target info without triggering state update
      crossContainerTarget.current = {
        targetColumn: overContainer,
        targetIndex: 0,
        overId: overId
      }
      return
    }

    // Store target info for handleDragEnd
    crossContainerTarget.current = {
      targetColumn: overContainer,
      targetIndex: 0, // Will be calculated in handleDragEnd based on over.id
      overId: overId
    }

    // Mark this container as last updated
    lastOverContainerRef.current = overContainer

    // Only update state when container actually changes (not on every pixel movement)
    setCards(prevCards => {
      const card = prevCards.find(c => c.id === active.id)
      // Skip update if card already in target container or not found
      if (!card || card.columnId === overContainer) return prevCards

      // Map columnId to status
      const statusMap: Record<string, string> = {
        'todo': 'Todo',
        'inprogress': 'InProgress',
        'review': 'Review',
        'done': 'Done',
        'archived': 'Archived',
      }

      const newCards = prevCards.map(c => 
        c.id === active.id 
          ? { ...c, columnId: overContainer, status: statusMap[overContainer] }
          : c
      )
      cardsRef.current = newCards
      return newCards
    })
  }, [findContainer])

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event
    const originalColumnId = clonedCardsRef.current?.find(c => c.id === active.id)?.columnId
    const savedClonedCards = clonedCardsRef.current

    // Always reset active state
    setActiveId(null)
    setClonedCards(null)
    clonedCardsRef.current = null
    activeCardRef.current = null
    lastOverContainerRef.current = null

    if (!over) return

    const overId = over.id as string
    
    // Use originalColumnId as activeContainer
    const activeContainer = originalColumnId
    
    // For overContainer: prioritize crossContainerTarget if available (most accurate)
    // Otherwise calculate from overId
    let overContainer: string | undefined
    if (crossContainerTarget.current) {
      overContainer = crossContainerTarget.current.targetColumn
    } else if (COLUMNS.some(col => col.id === overId)) {
      overContainer = overId
    } else {
      // Find from clonedCards (original state) to avoid issues with handleDragOver updates
      const clonedCardsSnapshot = clonedCardsRef.current as KanbanCardData[] | null
      if (clonedCardsSnapshot) {
        overContainer = clonedCardsSnapshot.find((c: KanbanCardData) => c.id === overId)?.columnId
      }
      if (!overContainer) {
        overContainer = cards.find(c => c.id === overId)?.columnId
      }
    }

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
      // Use cardsRef.current to get latest cards without triggering re-render
      const containerCards = cardsRef.current
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
            toast.success("Order updated")
          } catch (error) {
            toast.error("Failed to update order")
          }
        }
      }
    } else {
      // Cross-container move
      if (!originalColumnId) return

      // Get other cards in target container (excluding the moved card)
      // Use cardsRef.current to avoid dependency on cards state
      const otherCardsInTarget = cardsRef.current
        .filter(c => c.columnId === overContainer && c.id !== active.id)
        .sort((a, b) => (a.rank || 999) - (b.rank || 999))

      // Calculate newIndex based on over.id at drop time
      let newIndex: number
      if (COLUMNS.some(col => col.id === overId)) {
        // Dropped on column itself → append to end
        newIndex = otherCardsInTarget.length
      } else {
        // Dropped on a card → insert at that card's position
        const overIndex = otherCardsInTarget.findIndex(c => c.id === overId)
        newIndex = overIndex >= 0 ? overIndex : otherCardsInTarget.length
      }

      // Clear the ref
      crossContainerTarget.current = null

      // Build final ordered list: insert active card at newIndex
      const finalOrder = [...otherCardsInTarget]
      // Use original card from savedClonedCards to get correct dependencies data
      const activeCard = savedClonedCards?.find(c => c.id === active.id) || cardsRef.current.find(c => c.id === active.id)
      if (activeCard) {
        finalOrder.splice(newIndex, 0, activeCard)
      }

      // Validate dependencies - block move if dependencies not completed (except moving to Todo/Archived)
      if (activeCard && overContainer !== 'todo' && overContainer !== 'archived') {
        const { isBlocked, incompleteDeps } = checkDependenciesCompleted(activeCard, savedClonedCards || undefined)
        if (isBlocked) {
          toast.error(`Cannot move story: ${incompleteDeps.length} incomplete dependencies`)
          // Revert to original state
          if (savedClonedCards) {
            setCards(savedClonedCards)
          }
          return
        }
      }

      // Calculate new ranks
      const newRanks = new Map<string, number>()
      finalOrder.forEach((card, index) => {
        newRanks.set(card.id, index + 1)
      })

      // Update local state with columnId, status, and ranks
      setCards(prev => {
        // Map columnId to status
        const statusMap: Record<string, string> = {
          'todo': 'Todo',
          'inprogress': 'InProgress',
          'review': 'Review',
          'done': 'Done',
          'archived': 'Archived',
        }

        // First pass: update columnId, status, and ranks
        const updatedCards = prev.map(card => {
          if (card.id === active.id) {
            const newRank = newRanks.get(card.id)
            return { ...card, columnId: overContainer, status: statusMap[overContainer], rank: newRank ?? card.rank }
          }
          const newRank = newRanks.get(card.id)
          if (newRank !== undefined) {
            return { ...card, rank: newRank }
          }
          return card
        })
        
        // Second pass: recalculate isBlocked for cards that depend on the moved card
        const movedCardId = active.id as string
        return updatedCards.map(card => {
          // Only recalculate if this card depends on the moved card
          if (!card.dependencies?.includes(movedCardId)) {
            return card
          }
          // Calculate new blocked state
          const newIsBlocked = card.columnId !== 'done' && card.columnId !== 'archived' &&
            card.dependencies.some(depId => {
              const dep = updatedCards.find(c => c.id === depId)
              return dep && dep.columnId !== 'done' && dep.columnId !== 'archived'
            })
          const newBlockedByCount = card.dependencies.filter(depId => {
            const dep = updatedCards.find(c => c.id === depId)
            return dep && dep.columnId !== 'done' && dep.columnId !== 'archived'
          }).length
          
          // Only create new object if values changed
          if (card.isBlocked === newIsBlocked && card.blockedByCount === newBlockedByCount) {
            return card
          }
          return { ...card, isBlocked: newIsBlocked, blockedByCount: newBlockedByCount }
        })
      })

      // Save to backend
      try {
        await storiesApi.updateStatus(active.id as string, statusMap[overContainer] || 'Todo')
        
        const rankUpdates: { story_id: string; rank: number }[] = []
        newRanks.forEach((rank, cardId) => rankUpdates.push({ story_id: cardId, rank }))
        if (rankUpdates.length > 0) {
          await storiesApi.bulkUpdateRanks(rankUpdates)
        }
        toast.success("Story status updated")
      } catch (error) {
        toast.error("Failed to update status")
        // Revert to original state on error
        if (savedClonedCards) {
          setCards(savedClonedCards)
        }
      }
    }
  }, [findContainer, projectId, checkDependenciesCompleted])

  // Handle drag cancel - restore original state
  const handleDragCancel = useCallback(() => {
    // Use ref instead of state to avoid dependency
    if (clonedCardsRef.current) {
      setCards(clonedCardsRef.current)
    }
    setActiveId(null)
    setClonedCards(null)
    clonedCardsRef.current = null
    activeCardRef.current = null
    crossContainerTarget.current = null
    lastOverContainerRef.current = null
  }, [])

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
        status: "Todo",
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
      toast.error("Failed to update story")
    } finally {
      toast.dismiss(toastId)
    }
  }, [projectId, queryClient])

  const handleDeleteCard = useCallback(async (cardId: string) => {
    setCards(prev => prev.filter(card => card.id !== cardId))
    try {
      await storiesApi.delete(cardId)
      toast.success("Story deleted")
    } catch (error) {
      toast.error("Failed to delete story")
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

    // Validate dependencies - block move if dependencies not completed (except moving to Todo/Archived)
    if (targetColumnId !== 'todo' && targetColumnId !== 'archived') {
      const { isBlocked, incompleteDeps } = checkDependenciesCompleted(card)
      if (isBlocked) {
        toast.error(`Không thể di chuyển story: ${incompleteDeps.length} dependencies chưa hoàn thành`)
        return
      }
    }

    setCards(prev => {
      // Map columnId to status
      const statusMap: Record<string, string> = {
        'todo': 'Todo',
        'inprogress': 'InProgress',
        'review': 'Review',
        'done': 'Done',
        'archived': 'Archived',
      }

      // First pass: update columnId and status
      const updatedCards = prev.map(c =>
        c.id === cardId ? { ...c, columnId: targetColumnId, status: statusMap[targetColumnId] } : c
      )
      // Second pass: recalculate isBlocked only for cards that depend on the moved card
      return updatedCards.map(c => {
        if (!c.dependencies?.includes(cardId)) {
          return c
        }
        const newIsBlocked = c.columnId !== 'done' && c.columnId !== 'archived' &&
          c.dependencies.some(depId => {
            const dep = updatedCards.find(card => card.id === depId)
            return dep && dep.columnId !== 'done' && dep.columnId !== 'archived'
          })
        const newBlockedByCount = c.dependencies.filter(depId => {
          const dep = updatedCards.find(card => card.id === depId)
          return dep && dep.columnId !== 'done' && dep.columnId !== 'archived'
        }).length
        
        if (c.isBlocked === newIsBlocked && c.blockedByCount === newBlockedByCount) {
          return c
        }
        return { ...c, isBlocked: newIsBlocked, blockedByCount: newBlockedByCount }
      })
    })

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
      setCards(prev => prev.map(c =>
        c.id === cardId ? { ...c, columnId: card.columnId } : c
      ))
    }
  }, [cards, checkDependenciesCompleted])

  const handleEditCard = useCallback((card: KanbanCardData) => {
    setEditingStory({
      id: card.id,
      title: card.content,
      description: card.description,
      type: "UserStory",
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
                  {[{ value: "UserStory", label: "User Story" }].map((type) => (
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
        //allStories={columns.flatMap(col => col.cards)}
        projectId={projectId}
        allStories={cards}
        onViewFiles={onViewFiles}
      />

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
