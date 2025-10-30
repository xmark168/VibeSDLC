import { useEffect, useRef, useState, useCallback } from 'react'
import type { Message } from '@/types/message'

export type WebSocketMessage = {
  type: 'connected' | 'message' | 'agent_message' | 'typing' | 'pong' | 'error'
  data?: Message
  agent_name?: string
  is_typing?: boolean
  message?: string
  project_id?: string
}

export type SendMessageParams = {
  content: string
  author_type?: 'user' | 'agent'
}

export function useChatWebSocket(projectId: string | undefined, token: string | undefined) {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set())
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(() => {
    if (!projectId || !token) return

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
    const wsUrl = `${protocol}//${host}/api/v1/chat/ws?project_id=${projectId}&token=${token}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      reconnectAttemptsRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)
        
        switch (data.type) {
          case 'connected':
            console.log('Connected to chat:', data.message)
            break
            
          case 'message':
          case 'agent_message':
            if (data.data) {
              setMessages((prev) => {
                // Check if message already exists
                const exists = prev.some(m => m.id === data.data!.id)
                if (exists) return prev
                return [...prev, data.data!]
              })
            }
            break
            
          case 'typing':
            if (data.agent_name) {
              setTypingAgents((prev) => {
                const newSet = new Set(prev)
                if (data.is_typing) {
                  newSet.add(data.agent_name!)
                } else {
                  newSet.delete(data.agent_name!)
                }
                return newSet
              })
            }
            break
            
          case 'pong':
            // Handle ping/pong for keep-alive
            break
            
          case 'error':
            console.error('WebSocket error:', data.message)
            break
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      wsRef.current = null

      // Attempt to reconnect
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current})`)
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, delay)
      }
    }
  }, [projectId, token])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((params: SendMessageParams) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected')
      return false
    }

    try {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: params.content,
        author_type: params.author_type || 'user',
      }))
      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }, [])

  const ping = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])

  // Connect on mount and when dependencies change
  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const interval = setInterval(() => {
      ping()
    }, 30000)

    return () => clearInterval(interval)
  }, [isConnected, ping])

  return {
    isConnected,
    messages,
    typingAgents: Array.from(typingAgents),
    sendMessage,
    connect,
    disconnect,
  }
}
