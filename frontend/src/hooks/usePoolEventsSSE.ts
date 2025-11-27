/**
 * Server-Sent Events (SSE) hook for real-time pool updates
 * 
 * Connects to /api/v1/agent-management/pools/events and receives:
 * - pool_stats: Pool statistics updates every 5s
 * - agent_health: Agent health status updates
 * - heartbeat: Connection keepalive
 */

import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { agentQueryKeys } from '@/queries/agents'
import { OpenAPI } from '@/client'

interface PoolStatsEvent {
  pool_name: string
  active_agents: number
  busy_agents: number
  idle_agents: number
  total_spawned: number
  total_terminated: number
  is_running: boolean
}

interface AgentHealthEvent {
  agent_id: string
  pool_name: string
  state: string
  healthy: boolean
}

interface SSEState {
  connected: boolean
  error: string | null
  lastUpdate: Date | null
}

export function usePoolEventsSSE(options?: {
  enabled?: boolean
  onPoolStats?: (stats: PoolStatsEvent[]) => void
  onAgentHealth?: (health: AgentHealthEvent[]) => void
  onError?: (error: Error) => void
}) {
  const queryClient = useQueryClient()
  const eventSourceRef = useRef<EventSource | null>(null)
  const [state, setState] = useState<SSEState>({
    connected: false,
    error: null,
    lastUpdate: null,
  })

  const enabled = options?.enabled ?? true

  useEffect(() => {
    if (!enabled) {
      // Cleanup if disabled
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
        setState({ connected: false, error: null, lastUpdate: null })
      }
      return
    }

    // Get auth token
    const token = localStorage.getItem('access_token')
    if (!token) {
      setState({ connected: false, error: 'No authentication token', lastUpdate: null })
      return
    }

    // Build SSE URL with auth token
    const baseUrl = OpenAPI.BASE || ''
    const url = `${baseUrl}/api/v1/agent-management/pools/events`
    
    // EventSource doesn't support headers, so we need to pass token as query param
    // Alternative: use fetch with ReadableStream if you need headers
    const urlWithToken = `${url}?token=${encodeURIComponent(token)}`

    console.log('[SSE] Connecting to pool events stream...')

    // Create EventSource
    const eventSource = new EventSource(urlWithToken)
    eventSourceRef.current = eventSource

    // Handle connection open
    eventSource.addEventListener('open', () => {
      console.log('[SSE] Connected to pool events stream')
      setState((prev) => ({ ...prev, connected: true, error: null }))
    })

    // Handle 'connected' event
    eventSource.addEventListener('connected', (event) => {
      const data = JSON.parse(event.data)
      console.log('[SSE] Connection confirmed:', data.message)
    })

    // Handle 'pool_stats' event
    eventSource.addEventListener('pool_stats', (event) => {
      try {
        const stats: PoolStatsEvent[] = JSON.parse(event.data)
        console.log('[SSE] Pool stats update:', stats)

        // Update state
        setState((prev) => ({ ...prev, lastUpdate: new Date() }))

        // Call callback if provided
        options?.onPoolStats?.(stats)

        // Invalidate React Query cache to trigger refetch
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
      } catch (error) {
        console.error('[SSE] Error parsing pool_stats:', error)
      }
    })

    // Handle 'agent_health' event
    eventSource.addEventListener('agent_health', (event) => {
      try {
        const health: AgentHealthEvent[] = JSON.parse(event.data)
        console.log('[SSE] Agent health update:', health.length, 'agents')

        // Call callback if provided
        options?.onAgentHealth?.(health)

        // Invalidate health queries
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      } catch (error) {
        console.error('[SSE] Error parsing agent_health:', error)
      }
    })

    // Handle 'heartbeat' event
    eventSource.addEventListener('heartbeat', (event) => {
      try {
        const data = JSON.parse(event.data)
        // Silent heartbeat - just update timestamp
        setState((prev) => ({ ...prev, lastUpdate: new Date(data.timestamp) }))
      } catch (error) {
        console.error('[SSE] Error parsing heartbeat:', error)
      }
    })

    // Handle 'error' event from server
    eventSource.addEventListener('error_event', (event) => {
      try {
        const data = JSON.parse(event.data)
        console.error('[SSE] Server error:', data.error)
        setState((prev) => ({ ...prev, error: data.error }))
        options?.onError?.(new Error(data.error))
      } catch (error) {
        console.error('[SSE] Error parsing error event:', error)
      }
    })

    // Handle connection errors
    eventSource.onerror = (event) => {
      console.error('[SSE] Connection error:', event)
      
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('[SSE] Connection closed by server')
        setState({ connected: false, error: 'Connection closed', lastUpdate: null })
      } else if (eventSource.readyState === EventSource.CONNECTING) {
        console.log('[SSE] Reconnecting...')
        setState((prev) => ({ ...prev, connected: false, error: 'Reconnecting...' }))
      } else {
        setState((prev) => ({ ...prev, error: 'Connection error' }))
        options?.onError?.(new Error('SSE connection error'))
      }
    }

    // Cleanup on unmount
    return () => {
      console.log('[SSE] Closing connection...')
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [enabled, queryClient, options])

  return {
    connected: state.connected,
    error: state.error,
    lastUpdate: state.lastUpdate,
    disconnect: () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
        setState({ connected: false, error: null, lastUpdate: null })
      }
    },
  }
}
