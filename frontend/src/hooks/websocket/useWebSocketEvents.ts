/**
 * useWebSocketEvents - Event Emitter for WebSocket messages
 * 
 * Responsibilities:
 * - Parse incoming WebSocket messages
 * - Emit events to subscribers
 * - Handle ping/pong
 * 
 * This hook creates a simple pub/sub system for WebSocket events
 */

import { useEffect, useRef, useCallback } from 'react'

type EventHandler = (data: any) => void
type UnsubscribeFn = () => void

interface EventEmitter {
  on: (eventType: string, handler: EventHandler) => UnsubscribeFn
  emit: (eventType: string, data: any) => void
  off: (eventType: string, handler: EventHandler) => void
}

export interface UseWebSocketEventsOptions {
  /** WebSocket instance */
  ws: WebSocket | null
  /** Callback for pong responses */
  onPong?: () => void
}

export function useWebSocketEvents(options: UseWebSocketEventsOptions): EventEmitter {
  const { ws, onPong } = options
  
  // Store event handlers: eventType -> Set<handler>
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map())

  // Subscribe to event
  const on = useCallback((eventType: string, handler: EventHandler): UnsubscribeFn => {
    const handlers = handlersRef.current.get(eventType) || new Set()
    handlers.add(handler)
    handlersRef.current.set(eventType, handlers)

    // Return unsubscribe function
    return () => {
      const handlers = handlersRef.current.get(eventType)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          handlersRef.current.delete(eventType)
        }
      }
    }
  }, [])

  // Emit event to all subscribers
  const emit = useCallback((eventType: string, data: any) => {
    const handlers = handlersRef.current.get(eventType)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`[useWebSocketEvents] Error in handler for ${eventType}:`, error)
        }
      })
    }
  }, [])

  // Unsubscribe handler
  const off = useCallback((eventType: string, handler: EventHandler) => {
    const handlers = handlersRef.current.get(eventType)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        handlersRef.current.delete(eventType)
      }
    }
  }, [])

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!ws) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        const eventType = data.type

        // Handle ping/pong at this level
        if (eventType === 'ping') {
          // Send pong response
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'pong' }))
          }
          return
        }

        if (eventType === 'pong') {
          onPong?.()
          return
        }

        // Emit event to all subscribers
        emit(eventType, data)

      } catch (error) {
        console.error('[useWebSocketEvents] Failed to parse message:', error)
      }
    }

    ws.addEventListener('message', handleMessage)

    return () => {
      ws.removeEventListener('message', handleMessage)
    }
  }, [ws, emit, onPong])

  return { on, emit, off }
}
