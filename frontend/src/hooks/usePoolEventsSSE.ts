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
    

    const urlWithToken = `${url}?token=${encodeURIComponent(token)}`

    // Create EventSource
    const eventSource = new EventSource(urlWithToken)
    eventSourceRef.current = eventSource

    // Handle connection open
    eventSource.addEventListener('open', () => {
      setState((prev) => ({ ...prev, connected: true, error: null }))
    })

    // Handle 'connected' event
    eventSource.addEventListener('connected', (event) => {
      const data = JSON.parse(event.data)
    })

    // Handle 'pool_stats' event
    eventSource.addEventListener('pool_stats', (event) => {
      try {
        const stats: PoolStatsEvent[] = JSON.parse(event.data)

        // Update state
        setState((prev) => ({ ...prev, lastUpdate: new Date() }))

        // Call callback if provided
        options?.onPoolStats?.(stats)

        // Invalidate React Query cache to trigger refetch
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
      } catch (error) {
      }
    })

    // Handle 'agent_health' event
    eventSource.addEventListener('agent_health', (event) => {
      try {
        const health: AgentHealthEvent[] = JSON.parse(event.data)

        // Call callback if provided
        options?.onAgentHealth?.(health)

        // Invalidate health queries
        queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      } catch (error) {
      }
    })

    // Handle 'heartbeat' event
    eventSource.addEventListener('heartbeat', (event) => {
      try {
        const data = JSON.parse(event.data)
        setState((prev) => ({ ...prev, lastUpdate: new Date(data.timestamp) }))
      } catch (error) {
      }
    })

    eventSource.addEventListener('error_event', (event) => {
      try {
        const data = JSON.parse(event.data)
        setState((prev) => ({ ...prev, error: data.error }))
        options?.onError?.(new Error(data.error))
      } catch (error) {
      }
    })

    // Handle connection errors
    eventSource.onerror = (event) => {
      
      if (eventSource.readyState === EventSource.CLOSED) {
        setState({ connected: false, error: 'Connection closed', lastUpdate: null })
      } else if (eventSource.readyState === EventSource.CONNECTING) {
        setState((prev) => ({ ...prev, connected: false, error: 'Reconnecting...' }))
      } else {
        setState((prev) => ({ ...prev, error: 'Connection error' }))
        options?.onError?.(new Error('SSE connection error'))
      }
    }

    // Cleanup on unmount
    return () => {
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
