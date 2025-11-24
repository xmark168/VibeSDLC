/**
 * useKanbanUpdates - Kanban board updates hook
 * 
 * Responsibilities:
 * - Track kanban board state
 * - Monitor story events (created, updated, status changed)
 * - Handle tab switching
 * 
 * Now uses event emitter pattern
 */

import { useState, useCallback, useEffect } from 'react'

export interface KanbanBoard {
  Backlog: any[]
  Todo: any[]
  Doing: any[]
  Done: any[]
}

export interface KanbanData {
  sprints: any[]
  kanban_board: KanbanBoard
  total_items: number
  timestamp?: string
}

export interface UseKanbanUpdatesOptions {
  /** Event emitter from useWebSocketEvents */
  eventEmitter?: {
    on: (eventType: string, handler: (data: any) => void) => () => void
  }
  /** Callback when kanban data changes */
  onKanbanChange?: (data: KanbanData | null) => void
  /** Callback when active tab changes */
  onTabChange?: (tab: string | null) => void
}

export interface UseKanbanUpdatesReturn {
  /** Current kanban data */
  kanbanData: KanbanData | null
  /** Active tab */
  activeTab: string | null
  /** Clear kanban data */
  clearKanban: () => void
}

export function useKanbanUpdates(options: UseKanbanUpdatesOptions = {}): UseKanbanUpdatesReturn {
  const { eventEmitter, onKanbanChange, onTabChange } = options

  const [kanbanData, setKanbanData] = useState<KanbanData | null>(null)
  const [activeTab, setActiveTab] = useState<string | null>(null)

  // Subscribe to events
  useEffect(() => {
    if (!eventEmitter) return

    const unsubscribers: Array<() => void> = []

    // Handle kanban update events
    const handleKanbanUpdate = (data: any) => {
      if (data.data) {
        setKanbanData(data.data)
        onKanbanChange?.(data.data)
      }
    }

    // Handle tab switch events
    const handleSwitchTab = (data: any) => {
      if (data.tab) {
        setActiveTab(data.tab)
        onTabChange?.(data.tab)
      }
    }

    // Handle story events (just log, kanban will auto-refresh)
    const handleStoryEvent = (data: any) => {
      console.log('[useKanbanUpdates] Story event:', data.type, data.story_id)
    }

    // Subscribe to events
    unsubscribers.push(eventEmitter.on('kanban_update', handleKanbanUpdate))
    unsubscribers.push(eventEmitter.on('switch_tab', handleSwitchTab))
    unsubscribers.push(eventEmitter.on('story_created', handleStoryEvent))
    unsubscribers.push(eventEmitter.on('story_updated', handleStoryEvent))
    unsubscribers.push(eventEmitter.on('story_status_changed', handleStoryEvent))

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [eventEmitter, onKanbanChange, onTabChange])

  // Clear kanban data
  const clearKanban = useCallback(() => {
    setKanbanData(null)
    setActiveTab(null)
    onKanbanChange?.(null)
    onTabChange?.(null)
  }, [onKanbanChange, onTabChange])

  return {
    kanbanData,
    activeTab,
    clearKanban,
  }
}
