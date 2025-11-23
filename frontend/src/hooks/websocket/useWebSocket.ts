/**
 * useWebSocket - Base WebSocket connection hook
 * 
 * Responsibilities:
 * - Establish WebSocket connection
 * - Handle reconnection logic
 * - Send/receive raw messages
 * - Keep-alive ping/pong
 * - Connection state management
 * 
 * Does NOT handle:
 * - Message parsing/formatting
 * - Application-specific logic
 * - State management beyond connection
 */

import { useEffect, useRef, useState, useCallback } from 'react'

export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface UseWebSocketOptions {
  /** Project ID for WebSocket connection */
  projectId?: string
  /** Auth token */
  token?: string
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean
  /** Maximum reconnect attempts (default: 5) */
  maxReconnectAttempts?: number
  /** Enable keep-alive ping (default: true) */
  enablePing?: boolean
  /** Ping interval in ms (default: 30000) */
  pingInterval?: number
  /** Callback when connection state changes */
  onStateChange?: (state: WebSocketState) => void
  /** Callback when message received */
  onMessage?: (event: MessageEvent) => void
  /** Callback when error occurs */
  onError?: (error: Event) => void
}

export interface UseWebSocketReturn {
  /** Current connection state */
  state: WebSocketState
  /** Is connected and ready */
  isReady: boolean
  /** Send raw message */
  send: (data: string | object) => boolean
  /** Manually connect */
  connect: () => void
  /** Manually disconnect */
  disconnect: () => void
  /** Current reconnect attempt */
  reconnectAttempt: number
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    projectId,
    token,
    autoReconnect = true,
    maxReconnectAttempts = 5,
    enablePing = true,
    pingInterval = 30000,
    onStateChange,
    onMessage,
    onError,
  } = options

  const [state, setState] = useState<WebSocketState>('disconnected')
  const [reconnectAttempt, setReconnectAttempt] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const pingIntervalRef = useRef<NodeJS.Timeout | undefined>(undefined)

  // Update state and notify callback
  const updateState = useCallback((newState: WebSocketState) => {
    setState(newState)
    onStateChange?.(newState)
  }, [onStateChange])

  // Check if WebSocket is ready to send
  const isReady = useCallback(() => {
    return wsRef.current?.readyState === WebSocket.OPEN
  }, [])

  // Send message (string or object)
  const send = useCallback((data: string | object): boolean => {
    if (!isReady()) {
      console.warn('[useWebSocket] Cannot send - not connected')
      return false
    }

    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      wsRef.current!.send(message)
      return true
    } catch (error) {
      console.error('[useWebSocket] Failed to send message:', error)
      return false
    }
  }, [isReady])

  // Send ping
  const sendPing = useCallback(() => {
    send({ type: 'ping' })
  }, [send])

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!projectId || !token) {
      console.warn('[useWebSocket] Missing projectId or token')
      return
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    updateState('connecting')

    try {
      // Build WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
      const wsUrl = `${protocol}//${host}/api/v1/chat/ws?project_id=${projectId}&token=${token}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[useWebSocket] Connected')
        updateState('connected')
        setReconnectAttempt(0)

        // Start ping interval
        if (enablePing) {
          pingIntervalRef.current = setInterval(sendPing, pingInterval)
        }
      }

      ws.onmessage = (event) => {
        onMessage?.(event)
      }

      ws.onerror = (error) => {
        console.error('[useWebSocket] Error:', error)
        updateState('error')
        onError?.(error)
      }

      ws.onclose = () => {
        console.log('[useWebSocket] Disconnected')
        updateState('disconnected')
        wsRef.current = null

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = undefined
        }

        // Auto-reconnect
        if (autoReconnect && reconnectAttempt < maxReconnectAttempts) {
          const nextAttempt = reconnectAttempt + 1
          setReconnectAttempt(nextAttempt)

          const delay = Math.min(1000 * Math.pow(2, nextAttempt), 30000)
          console.log(`[useWebSocket] Reconnecting in ${delay}ms (attempt ${nextAttempt}/${maxReconnectAttempts})`)

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      }
    } catch (error) {
      console.error('[useWebSocket] Failed to connect:', error)
      updateState('error')
    }
  }, [
    projectId,
    token,
    autoReconnect,
    maxReconnectAttempts,
    reconnectAttempt,
    enablePing,
    pingInterval,
    sendPing,
    updateState,
    onMessage,
    onError,
  ])

  // Disconnect
  const disconnect = useCallback(() => {
    console.log('[useWebSocket] Disconnecting')

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = undefined
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setReconnectAttempt(0)
    updateState('disconnected')
  }, [updateState])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    state,
    isReady: state === 'connected',
    send,
    connect,
    disconnect,
    reconnectAttempt,
  }
}
