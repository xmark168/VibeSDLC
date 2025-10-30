/**
 * WebSocket utility functions and configuration
 */

export function getWebSocketUrl(path: string, params?: Record<string, string>): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8001'
  
  const queryString = params 
    ? '?' + new URLSearchParams(params).toString()
    : ''
  
  return `${protocol}//${host}${path}${queryString}`
}

export function createWebSocket(url: string): WebSocket {
  return new WebSocket(url)
}
