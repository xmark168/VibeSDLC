/**
 * Story WebSocket Hook - Real-time messages for story discussion
 * 
 * Subscribes to story_message events via existing WebSocket infrastructure
 */

import { useEffect, useState, useRef } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'

interface StoryMessage {
  id: string
  author: string
  author_type: 'user' | 'agent'
  content: string
  timestamp: string
}

interface UseStoryWebSocketReturn {
  messages: StoryMessage[]
  isConnected: boolean
  isLoading: boolean
  clearMessages: () => void
}

function getWebSocketUrl(projectId: string, token: string): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = import.meta.env.DEV ? '8000' : window.location.port
  const portStr = port ? `:${port}` : ''
  
  return `${wsProtocol}//${host}${portStr}/api/v1/chat/ws?project_id=${projectId}&token=${token}`
}

export function useStoryWebSocket(
  storyId: string | null,
  projectId: string | null,
  token: string | undefined,
  initialMessages: StoryMessage[] = []
): UseStoryWebSocketReturn {
  const [messages, setMessages] = useState<StoryMessage[]>(initialMessages)
  const [isLoading, setIsLoading] = useState(true)
  const storyIdRef = useRef(storyId)
  const prevStoryIdRef = useRef<string | null>(null)

  // Update ref when storyId changes
  useEffect(() => {
    storyIdRef.current = storyId
  }, [storyId])

  // Reset when story changes
  useEffect(() => {
    if (storyId && storyId !== prevStoryIdRef.current) {
      prevStoryIdRef.current = storyId
      setMessages([])
      setIsLoading(true)
    }
  }, [storyId])

  // Sync messages when initialMessages change (from API fetch)
  // This handles both empty and non-empty arrays
  useEffect(() => {
    // Only update if we have a valid storyId and initialMessages is the result of a fetch
    // (not the initial empty array from reset)
    if (storyId && prevStoryIdRef.current === storyId) {
      setMessages(initialMessages)
      setIsLoading(false) // Always stop loading after receiving data (even if empty)
    }
  }, [initialMessages, storyId])

  // WebSocket URL
  const socketUrl = projectId && token && storyId ? getWebSocketUrl(projectId, token) : null

  const { lastJsonMessage, readyState } = useWebSocket(
    socketUrl,
    {
      shouldReconnect: (closeEvent) => {
        // Don't reconnect on normal closure (1000) or policy violation (1008)
        if (closeEvent.code === 1000 || closeEvent.code === 1008) {
          return false
        }
        return true
      },
      reconnectAttempts: 10,  // Increased from 5 for better resilience
      reconnectInterval: (attemptNumber) => 
        Math.min(1000 * Math.pow(2, attemptNumber), 30000),  // Max 30s between attempts
      share: true,
      retryOnError: true,
      onReconnectStop: (numAttempts) => {
        console.warn(`[WebSocket] Reconnection stopped after ${numAttempts} attempts for story ${storyIdRef.current}`)
      },
      onOpen: () => {
        console.log(`[WebSocket] Connected for story ${storyIdRef.current}`)
      },
      onClose: (event) => {
        console.log(`[WebSocket] Closed (code: ${event.code}) for story ${storyIdRef.current}`)
      },
    },
    !!socketUrl
  )

  // Handle incoming messages
  useEffect(() => {
    if (!lastJsonMessage) return
    
    const msg = lastJsonMessage as any
    
    // Only handle story_message events for this story
    if (msg.type === 'story_message' && msg.story_id === storyIdRef.current) {
      const newMessage: StoryMessage = {
        id: msg.message_id || `ws_${Date.now()}`,
        author: msg.author_name || 'Unknown',
        author_type: msg.author_type === 'agent' ? 'agent' : 'user',
        content: msg.content || '',
        timestamp: msg.timestamp || new Date().toISOString(),
      }

      setMessages(prev => {
        // Avoid duplicates
        if (prev.some(m => m.id === newMessage.id)) {
          return prev
        }
        return [...prev, newMessage]
      })
    }
  }, [lastJsonMessage])

  const isConnected = readyState === ReadyState.OPEN
  
  const clearMessages = () => {
    setMessages([])
  }

  return {
    messages,
    isConnected,
    isLoading,
    clearMessages,
  }
}
