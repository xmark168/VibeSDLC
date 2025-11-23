/**
 * useKanbanUpdates - Kanban board updates hook
 * 
 * Responsibilities:
 * - Track kanban board state
 * - Monitor story events (created, updated, status changed)
 * - Handle tab switching
 * - Update kanban data
 * 
 * Depends on: WebSocket message events
 */

import { useState, useCallback } from 'react'

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
  /** Callback when message received */
  onMessage?: (event: MessageEvent) => void
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
  const { onMessage, onKanbanChange, onTabChange } = options

  const [kanbanData, setKanbanData] = useState<KanbanData | null>(null)
  const [activeTab, setActiveTab] = useState<string | null>(null)

  // Handle incoming WebSocket message
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'kanban_update': {
          if (data.data) {
            setKanbanData(data.data)
            onKanbanChange?.(data.data)
          }
          break
        }

        case 'switch_tab': {
          if (data.tab) {
            setActiveTab(data.tab)
            onTabChange?.(data.tab)
          }
          break
        }

        case 'story_created':
        case 'story_updated':
        case 'story_status_changed': {
          // Story events trigger kanban refresh
          // Kanban will auto-refresh via kanban_update event
          console.log('[useKanbanUpdates] Story event:', data.type, data.story_id)
          break
        }

        default:
          // Not a kanban type we handle
          break
      }

      // Forward to parent callback
      onMessage?.(event)
    } catch (error) {
      console.error('[useKanbanUpdates] Failed to parse message:', error)
    }
  }, [onMessage, onKanbanChange, onTabChange])

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
