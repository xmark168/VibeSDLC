
import { Download, Zap, User, Users, Flag, Calendar, ChevronRight, MessageSquare, FileText, ScrollText, Send, Paperclip, Smile, Link2, ExternalLink, Loader2, Wifi, WifiOff, Square, RotateCcw, GitBranch, Plus, Minus, FileCode, Pause, Play, AlertTriangle, Eye, Trash2, Activity, Sparkles } from "lucide-react"
import { toast } from "@/lib/toast"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ui/ai/conversation"
import {
  Message,
  MessageContent,
  MessageAvatar,
} from "@/components/ui/ai/message"
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputTools,
  PromptInputButton,
  PromptInputSubmit,
} from "@/components/ui/ai/prompt-input"
import {
  Task,
  TaskTrigger,
  TaskContent,
  TaskItem,
} from "@/components/ui/ai/task"
import type { KanbanCardData } from "./kanban-card"
import React, { useState, useRef, useEffect, useCallback, useMemo } from "react"
import { useStoryWebSocket } from "@/hooks/useStoryWebSocket"
import { ErrorBoundary } from "@/components/shared/error-boundary"

// DiffsView component for showing git diffs
interface DiffFile {
  status: string
  filename: string
  additions: number
  deletions: number
  binary: boolean
}

interface DiffData {
  files: DiffFile[]
  file_count: number
  total_additions: number
  total_deletions: number
  diff: string
  base_branch: string | null
}

function DiffsView({ storyId, onViewInFiles }: { storyId: string, onViewInFiles?: () => void }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [diffs, setDiffs] = useState<DiffData | null>(null)
  
  useEffect(() => {
    const fetchDiffs = async () => {
      setLoading(true)
      setError(null)
      try {
        const token = localStorage.getItem('access_token')
        const response = await fetch(
          `${import.meta.env.VITE_API_URL}/api/v1/stories/${storyId}/diffs`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )
        if (response.ok) {
          setDiffs(await response.json())
        } else {
          setError('Failed to load diffs')
        }
      } catch {
        setError('Failed to load diffs')
      } finally {
        setLoading(false)
      }
    }
    fetchDiffs()
  }, [storyId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center text-destructive py-8">
        <p className="text-sm">{error}</p>
      </div>
    )
  }

  if (!diffs || diffs.files.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No changes detected</p>
        {diffs?.base_branch && <p className="text-xs mt-1">Comparing to {diffs.base_branch}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground">{diffs.file_count} files changed</span>
          <span className="text-green-600 font-medium">+{diffs.total_additions}</span>
          <span className="text-red-500 font-medium">-{diffs.total_deletions}</span>
        </div>
        <div className="flex items-center gap-2">
          {diffs.base_branch && (
            <span className="text-xs text-muted-foreground">vs {diffs.base_branch}</span>
          )}
          {onViewInFiles && (
            <Button size="sm" variant="default" onClick={onViewInFiles} className="h-7 text-xs">
              <Eye className="w-3 h-3 mr-1" />
              View Files
            </Button>
          )}
        </div>
      </div>
      
      {/* File list */}
      <div className="border rounded-lg">
        <div className="px-3 py-2 bg-muted/50 border-b text-xs font-medium text-muted-foreground flex items-center gap-2">
          <FileCode className="w-4 h-4" />
          Changed Files
        </div>
        <div className="divide-y">
          {diffs.files.map((file, idx) => (
            <div key={idx} className="px-3 py-2 text-xs flex items-center gap-2 hover:bg-muted/30">
              {file.status === 'A' && <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-green-500/10 text-green-600 border-green-500/30">A</Badge>}
              {file.status === 'M' && <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-amber-500/10 text-amber-600 border-amber-500/30">M</Badge>}
              {file.status === 'D' && <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-red-500/10 text-red-500 border-red-500/30">D</Badge>}
              {!['A', 'M', 'D'].includes(file.status) && <Badge variant="outline" className="text-[10px] px-1.5 py-0">{file.status}</Badge>}
              <span className="font-mono truncate flex-1">{file.filename}</span>
              {!file.binary ? (
                <span className="text-muted-foreground font-mono">
                  <span className="text-green-600">+{file.additions}</span>
                  {' '}
                  <span className="text-red-500">-{file.deletions}</span>
                </span>
              ) : (
                <span className="text-muted-foreground text-[10px]">binary</span>
              )}
            </div>
          ))}
        </div>
      </div>
      
      {/* Diff content */}
      {diffs.diff && (
        <div className="border rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-muted/50 border-b text-xs font-medium text-muted-foreground">
            Diff
          </div>
          <pre className="p-3 text-xs font-mono overflow-x-auto bg-muted/20 max-h-[400px] overflow-y-auto whitespace-pre">
            {diffs.diff}
          </pre>
        </div>
      )}
    </div>
  )
}

// PreviewDialog component - Fullscreen iframe preview via backend proxy
function PreviewDialog({ storyId, storyTitle, runningPort, open, onOpenChange }: { 
  storyId: string
  storyTitle: string
  runningPort?: number | null
  open: boolean
  onOpenChange: (open: boolean) => void 
}) {
  const [iframeKey, setIframeKey] = useState(0)
  
  // Direct iframe to dev server - no proxy needed
  const previewUrl = runningPort ? `http://localhost:${runningPort}` : null

  const handleRefresh = () => setIframeKey(prev => prev + 1)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-none !w-screen !h-screen !max-h-screen !rounded-none !p-0 !gap-0 !translate-x-0 !translate-y-0 !top-0 !left-0 fixed inset-0">
        <DialogHeader className="px-4 py-3 border-b shrink-0 flex flex-row items-center justify-between">
          <div>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              Preview: {storyTitle}
            </DialogTitle>
            <DialogDescription className="sr-only">
              Live preview of the application
            </DialogDescription>
          </div>
          {previewUrl && (
            <Button variant="ghost" size="sm" onClick={handleRefresh} className="mr-8">
              <RotateCcw className="w-4 h-4 mr-1" />
              Refresh
            </Button>
          )}
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>
          {!runningPort ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <AlertTriangle className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">Dev server not running</p>
              <p className="text-sm mt-2">Start the dev server first using the "Dev Server" button</p>
            </div>
          ) : (
            <iframe
              key={iframeKey}
              src={previewUrl!}
              className="w-full h-full border-0"
              title="App Preview"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface TaskDetailModalProps {
  card: KanbanCardData | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadResult: (card: KanbanCardData) => void
  allStories?: KanbanCardData[]  // For resolving dependency titles
  projectId?: string  // For WebSocket connection
  onViewFiles?: (worktreePath: string) => void  // Navigate to files tab in workspace
}

// Mock chat messages type
interface ChatMessage {
  id: string
  author: string
  author_type: 'user' | 'agent'
  content: string
  timestamp: string
  avatar?: string
  message_type?: 'text' | 'task' | 'system' | 'log'
}

// Epic info for popup
interface EpicInfo {
  epic_code?: string
  epic_title?: string
  epic_id?: string
  description?: string
  domain?: string
}

export function TaskDetailModal({ card, open, onOpenChange, onDownloadResult, allStories = [], projectId, onViewFiles }: TaskDetailModalProps) {
  const [selectedChild, setSelectedChild] = useState<KanbanCardData | null>(null)
  const [selectedDependency, setSelectedDependency] = useState<KanbanCardData | null>(null)
  const [selectedEpic, setSelectedEpic] = useState<EpicInfo | null>(null)
  const [localAgentState, setLocalAgentState] = useState<string | null>(null)
  const [localPrState, setLocalPrState] = useState<string | null>(null)
  const [localStatus, setLocalStatus] = useState<string | null>(null)
  
  // Sync local state with card prop
  useEffect(() => {
    if (card?.agent_state) {
      setLocalAgentState(card.agent_state)
    }
    if (card?.pr_state) {
      setLocalPrState(card.pr_state)
    }
    if (card?.status) {
      setLocalStatus(card.status)
    }
  }, [card?.agent_state, card?.pr_state, card?.status])
  
  // Listen for story state changes via WebSocket
  useEffect(() => {
    const handleStoryStateChanged = (event: CustomEvent) => {
      console.log('[TaskDetailModal] Received story-state-changed:', event.detail, 'card?.id:', card?.id)
      if (event.detail.story_id === card?.id) {
        if (event.detail.agent_state !== undefined) {
          console.log('[TaskDetailModal] Updating localAgentState to:', event.detail.agent_state)
          setLocalAgentState(event.detail.agent_state)
        }
        if (event.detail.pr_state !== undefined) {
          console.log('[TaskDetailModal] Updating localPrState to:', event.detail.pr_state)
          setLocalPrState(event.detail.pr_state)
        }
      }
    }
    
    // Also listen for story-status-changed (merge success sends this)
    const handleStoryStatusChanged = (event: CustomEvent) => {
      console.log('[TaskDetailModal] Received story-status-changed:', event.detail, 'card?.id:', card?.id)
      if (event.detail.story_id === card?.id) {
        if (event.detail.pr_state !== undefined) {
          console.log('[TaskDetailModal] Updating localPrState to:', event.detail.pr_state)
          setLocalPrState(event.detail.pr_state)
        }
        if (event.detail.status !== undefined) {
          console.log('[TaskDetailModal] Updating localStatus to:', event.detail.status)
          setLocalStatus(event.detail.status)
        }
      }
    }
    
    window.addEventListener('story-state-changed', handleStoryStateChanged as EventListener)
    window.addEventListener('story-status-changed', handleStoryStatusChanged as EventListener)
    return () => {
      window.removeEventListener('story-state-changed', handleStoryStateChanged as EventListener)
      window.removeEventListener('story-status-changed', handleStoryStatusChanged as EventListener)
    }
  }, [card?.id])
  
  // Use local state for agent_state, pr_state, and status display
  const agentState = localAgentState || card?.agent_state
  const prState = localPrState || card?.pr_state
  const status = localStatus || card?.status
  
  // Get token from localStorage
  const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  
  // Helper to get story title from dependency ID (UUID)
  const getDependencyTitle = (depId: string): string => {
    const story = allStories.find(s => s.id === depId)
    if (story) {
      // Truncate long titles
      const title = story.content || 'Untitled'
      return title.length > 50 ? title.substring(0, 50) + '...' : title
    }
    // Fallback: show shortened UUID
    return depId.substring(0, 8) + '...'
  }
  const [activeTab, setActiveTab] = useState<string>("detail")
  const [chatMessage, setChatMessage] = useState("")
  const [initialMessages, setInitialMessages] = useState<ChatMessage[]>([])
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isActionLoading, setIsActionLoading] = useState(false)
  
  // Reset to detail tab if current tab is hidden (Done/Archived status)
  useEffect(() => {
    if ((status === 'Done' || status === 'Archived') && (activeTab === 'chat' || activeTab === 'diffs')) {
      setActiveTab('detail')
    }
  }, [status, activeTab])
  const [showPreviewDialog, setShowPreviewDialog] = useState(false)
  const [storyLogs, setStoryLogs] = useState<Array<{id: string, content: string, level: string, timestamp: string, node: string}>>([])
  const logsScrollRef = useRef<HTMLDivElement>(null)
  const token = getToken()
  
  // Listen for story log messages from WebSocket
  useEffect(() => {
    if (!card?.id) return
    
    const handleStoryLog = (event: CustomEvent) => {
      const { story_id, content, level, node, timestamp } = event.detail
      if (story_id === card.id) {
        setStoryLogs(prev => [...prev, {
          id: `${Date.now()}-${Math.random()}`,
          content: content || '',
          level: level || 'info',
          timestamp: timestamp || new Date().toISOString(),
          node: node || ''
        }])
      }
    }
    
    window.addEventListener('story-log', handleStoryLog as EventListener)
    return () => window.removeEventListener('story-log', handleStoryLog as EventListener)
  }, [card?.id])
  
  // Fetch historical logs and clear when modal opens for a new card
  useEffect(() => {
    if (open && card?.id) {
      setStoryLogs([])
      // Fetch historical logs from API
      const fetchLogs = async () => {
        try {
          const authToken = getToken()
          const response = await fetch(
            `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/logs`,
            {
              headers: { 'Authorization': `Bearer ${authToken}` }
            }
          )
          if (response.ok) {
            const data = await response.json()
            setStoryLogs(data.logs.map((log: any) => ({
              id: log.id,
              content: log.content,
              level: log.level,
              timestamp: log.timestamp,
              node: log.node
            })))
          }
        } catch (error) {
          console.error('Failed to fetch logs:', error)
        }
      }
      fetchLogs()
    }
  }, [open, card?.id])
  
  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (logsScrollRef.current && storyLogs.length > 0) {
      // Use setTimeout to ensure DOM has updated
      setTimeout(() => {
        logsScrollRef.current?.scrollTo({
          top: logsScrollRef.current.scrollHeight,
          behavior: 'smooth'
        })
      }, 50)
    }
  }, [storyLogs])

  // Cancel task handler
  const handleCancelTask = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/cancel`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Task cancelled')
      } else {
        toast.error('Failed to cancel task')
      }
    } catch (error) {
      toast.error('Failed to cancel task')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Restart task handler
  const handleRestartTask = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/restart`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Task restarted')
      } else {
        toast.error('Failed to restart task')
      }
    } catch (error) {
      toast.error('Failed to restart task')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Merge to Main handler - triggers Developer agent to merge branch
  const handleMergeToMain = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/merge-to-main`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Merge started. Check logs for progress.')
      } else {
        const data = await response.json()
        toast.error(data.detail || 'Failed to start merge')
      }
    } catch (error) {
      toast.error('Failed to start merge')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Review story handler - triggers BA agent to verify and suggest improvements
  const handleReviewStory = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/review`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Đang phân tích story...')
        onOpenChange(false) // Close the modal
      } else {
        const error = await response.json().catch(() => ({}))
        toast.error(error.detail || 'Failed to review story')
      }
    } catch (error) {
      toast.error('Failed to review story')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Pause task handler
  const handlePauseTask = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/pause`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Task paused')
      } else {
        toast.error('Failed to pause task')
      }
    } catch (error) {
      toast.error('Failed to pause task')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Resume task handler
  const handleResumeTask = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/resume`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Task resumed')
      } else {
        toast.error('Failed to resume task')
      }
    } catch (error) {
      toast.error('Failed to resume task')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Start dev server handler
  const handleStartDevServer = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/dev-server/start`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        const data = await response.json()
        toast.success(`Dev server started on port ${data.port}`)
      } else {
        toast.error('Failed to start dev server')
      }
    } catch (error) {
      toast.error('Failed to start dev server')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Stop dev server handler
  const handleStopDevServer = async () => {
    if (!card?.id) return
    setIsActionLoading(true)
    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/dev-server/stop`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      if (response.ok) {
        toast.success('Dev server stopped')
      } else {
        toast.error('Failed to stop dev server')
      }
    } catch (error) {
      toast.error('Failed to stop dev server')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Fetch initial messages from API
  const fetchMessages = useCallback(async (storyId: string) => {
    const authToken = getToken()
    console.log('[fetchMessages] storyId:', storyId, 'token:', authToken ? 'exists' : 'missing')
    if (!storyId || !authToken) {
      console.log('[fetchMessages] Skipping - missing storyId or token')
      return
    }
    
    const apiUrl = `${import.meta.env.VITE_API_URL}/api/v1/stories/${storyId}/messages`
    console.log('[fetchMessages] Fetching:', apiUrl)
    
    setIsLoadingMessages(true)
    try {
      const response = await fetch(
        apiUrl,
        {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      )
      
      console.log('[fetchMessages] Response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('[fetchMessages] Data:', data)
        setInitialMessages(
          data.data.map((msg: {
            id: string
            author_name: string
            author_type: string
            content: string
            created_at: string
          }) => ({
            id: msg.id,
            author: msg.author_name || 'Unknown',
            author_type: msg.author_type === 'agent' ? 'agent' : 'user',
            content: msg.content,
            timestamp: msg.created_at,
          }))
        )
      } else {
        console.error('[fetchMessages] Error response:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('[fetchMessages] Failed to fetch story messages:', error)
    } finally {
      setIsLoadingMessages(false)
    }
  }, [])

  // Reset and fetch messages when dialog opens or card changes
  useEffect(() => {
    console.log('[useEffect] open:', open, 'card?.id:', card?.id)
    
    if (open && card?.id) {
      setInitialMessages([])
      console.log('[useEffect] Triggering fetchMessages for:', card.id)
      fetchMessages(card.id)
    }
  }, [open, card?.id, fetchMessages])

  // WebSocket for real-time messages
  const { messages: chatMessages, isConnected, isAgentThinking, clearMessages } = useStoryWebSocket(
    open ? card?.id ?? null : null,
    projectId ?? null,
    token ?? undefined,
    initialMessages
  )

  if (!card) return null

  const handleSendMessage = async () => {
    if (!chatMessage.trim() || !card?.id) return

    const messageContent = chatMessage.trim()
    setChatMessage("") // Clear immediately for better UX

    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/messages`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content: messageContent }),
        }
      )

      if (!response.ok) {
        // Restore message on error
        setChatMessage(messageContent)
        console.error('Failed to send message:', response.status)
      }
      // Message will arrive via WebSocket, no need to manually add
    } catch (error) {
      // Restore message on error
      setChatMessage(messageContent)
      console.error('Failed to send message:', error)
    }
  }

  const handleClearMessages = async () => {
    if (!card?.id) return

    try {
      const authToken = getToken()
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/stories/${card.id}/messages`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      )

      if (response.ok) {
        clearMessages() // Clear local state
        toast.success('Messages cleared')
      } else {
        toast.error('Failed to clear messages')
      }
    } catch (error) {
      console.error('Failed to clear messages:', error)
      toast.error('Failed to clear messages')
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Vừa xong'
    if (diffMins < 60) return `${diffMins} phút trước`
    if (diffHours < 24) return `${diffHours} giờ trước`
    if (diffDays < 7) return `${diffDays} ngày trước`

    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Get type badge color - Lean Kanban: UserStory, EnablerStory on board; Epic as parent
  const getTypeBadgeColor = (type?: string) => {
    const normalizedType = type?.toUpperCase()
    switch (normalizedType) {
      case "EPIC":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "USERSTORY":
      case "USER_STORY":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "ENABLERSTORY":
      case "ENABLER_STORY":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Format type name for display (UserStory/USER_STORY -> User Story)
  const formatTypeName = (type?: string) => {
    if (!type) return ""
    const normalizedType = type.toUpperCase()
    switch (normalizedType) {
      case "USERSTORY":
      case "USER_STORY":
        return "User Story"
      case "ENABLERSTORY":
      case "ENABLER_STORY":
        return "Enabler Story"
      case "EPIC":
        return "Epic"
      default:
        return type
    }
  }

  // Get status badge color
  const getStatusBadgeColor = (status?: string) => {
    switch (status) {
      case "Backlog":
        return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20"
      case "Todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "InProgress":
      case "Doing":
        return "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20"
      case "Review":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "Done":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Format status name for display
  const formatStatusName = (status?: string) => {
    switch (status) {
      case "InProgress": return "In Progress"
      case "Todo": return "To Do"
      default: return status
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col overflow-hidden" aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {card.story_code && (
                  <Badge
                    variant="default"
                    className="bg-primary/90 hover:bg-primary text-primary-foreground font-mono font-semibold tracking-wide cursor-pointer"
                    title="Click to copy"
                    onClick={() => {
                      navigator.clipboard.writeText(card.story_code || '')
                      toast.success('Story code copied!')
                    }}
                  >
                    {card.story_code}
                  </Badge>
                )}
                {card.type && (
                  <Badge variant="outline" className={getTypeBadgeColor(card.type)}>
                    {formatTypeName(card.type)}
                  </Badge>
                )}
              </div>
              <div className="text-base font-semibold text-foreground">{card.content}</div>
              
              {/* Task Details Grid */}
              {(card.started_at || agentState || card.branch_name || card.merge_status || card.running_port) && (
                <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 p-3 rounded-lg bg-muted/30 border text-xs">
                  {card.started_at && (
                    <>
                      <span className="text-muted-foreground font-medium">STARTED</span>
                      <span>{new Date(card.started_at).toLocaleString('vi-VN')}</span>
                    </>
                  )}
                  {agentState && (
                    <>
                      <span className="text-muted-foreground font-medium">AGENT STATUS</span>
                      <span className="flex items-center gap-1.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${
                          agentState === 'PROCESSING' ? 'bg-primary animate-pulse' :
                          agentState === 'PAUSED' ? 'bg-amber-500' :
                          agentState === 'FINISHED' ? 'bg-green-500' :
                          agentState === 'CANCELED' ? 'bg-destructive' :
                          'bg-muted-foreground'
                        }`}></span>
                        {agentState === 'PROCESSING' ? 'Processing' :
                         agentState === 'PAUSED' ? 'Paused' :
                         agentState === 'FINISHED' ? 'Finished' :
                         agentState === 'CANCELED' ? 'Canceled' : 'Pending'}
                      </span>
                    </>
                  )}
                  {card.branch_name && (
                    <>
                      <span className="text-muted-foreground font-medium">BRANCH</span>
                      <code className="bg-muted px-1.5 py-0.5 rounded text-[11px]">{card.branch_name}</code>
                    </>
                  )}
                  {card.merge_status !== undefined && (
                    <>
                      <span className="text-muted-foreground font-medium">MERGE STATUS</span>
                      <span className="flex items-center gap-1.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${
                          card.merge_status === 'merged' ? 'bg-green-500' :
                          card.merge_status === 'conflict' ? 'bg-destructive' :
                          'bg-amber-500'
                        }`}></span>
                        {card.merge_status === 'merged' ? 'Merged' :
                         card.merge_status === 'conflict' ? 'Conflict' : 'Not merged'}
                      </span>
                    </>
                  )}
                  {card.running_port && (
                    <>
                      <span className="text-muted-foreground font-medium">DEV SERVER</span>
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
                        Running on :{card.running_port}
                      </span>
                    </>
                  )}

                </div>
              )}

              {/* Action Buttons - show when agentState exists OR when in InProgress/Review */}
              {(agentState || status === 'InProgress' || status === 'Review') && (
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  {/* Dev Server Start */}
                  {agentState === 'FINISHED' && card.worktree_path && !card.running_port && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleStartDevServer}
                      disabled={isActionLoading}
                    >
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                      Dev Server
                    </Button>
                  )}
                  
                  {/* Dev Server Stop - danger color */}
                  {agentState === 'FINISHED' && card.worktree_path && card.running_port && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleStopDevServer}
                      disabled={isActionLoading}
                    >
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
                      Stop Server
                    </Button>
                  )}
                  
                  {/* Open App - success/green color */}
                  {card.running_port && (
                    <Button variant="outline" size="sm" className="border-green-500 text-green-600 hover:bg-green-50 hover:text-green-700" asChild>
                      <a href={`http://localhost:${card.running_port}`} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4" />
                        Open App
                      </a>
                    </Button>
                  )}
                  
                  {/* Preview - opens fullscreen preview dialog (requires running dev server) */}
                  {card.running_port && (
                    <Button variant="outline" size="sm" onClick={() => setShowPreviewDialog(true)}>
                      <Eye className="w-4 h-4" />
                      Preview
                    </Button>
                  )}

                  {/* Agent control buttons - only show in InProgress or Review columns */}
                  {(status === 'InProgress' || status === 'Review') && (
                    <>
                      {/* Waiting for agent when no state yet (just moved to InProgress, agent auto-triggered) */}
                      {!agentState && (
                        <Button variant="outline" size="sm" disabled className="text-muted-foreground">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Đang khởi tạo...
                        </Button>
                      )}
                      
                      {/* Pause when pending or processing */}
                      {(agentState === 'PENDING' || agentState === 'PROCESSING') && (
                        <Button variant="outline" size="sm" onClick={handlePauseTask} disabled={isActionLoading}>
                          {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pause className="w-4 h-4" />}
                          Tạm dừng
                        </Button>
                      )}
                      
                      {/* Resume when paused */}
                      {agentState === 'PAUSED' && (
                        <Button variant="default" size="sm" onClick={handleResumeTask} disabled={isActionLoading}>
                          {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                          Tiếp tục
                        </Button>
                      )}
                      
                      {/* Cancel when processing or paused */}
                      {(agentState === 'PENDING' || agentState === 'PROCESSING' || agentState === 'PAUSED') && (
                        <Button variant="destructive" size="sm" className="bg-red-600 hover:bg-red-700 text-white" onClick={handleCancelTask} disabled={isActionLoading}>
                          {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
                          Hủy
                        </Button>
                      )}
                      
                      {/* Restart when canceled or finished */}
                      {(agentState === 'CANCELED' || agentState === 'FINISHED') && (
                        <Button variant="default" size="sm" onClick={handleRestartTask} disabled={isActionLoading}>
                          {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                          Restart
                        </Button>
                      )}
                    </>
                  )}
                  
                  {/* Merge to Main when finished, not yet merged, not merging, and status is InProgress or Review */}
                  {agentState === 'FINISHED' && card.merge_status !== 'merged' && prState !== 'merging' && (status === 'InProgress' || status === 'Review') && (
                    <Button variant="default" size="sm" onClick={handleMergeToMain} disabled={isActionLoading} className="bg-green-600 hover:bg-green-700 text-white">
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
                      Merge to Main
                    </Button>
                  )}
                  
                  {/* Show merging indicator */}
                  {prState === 'merging' && (
                    <Button variant="outline" size="sm" disabled className="text-amber-600 border-amber-500">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Merging...
                    </Button>
                  )}
                </div>
              )}
              
              {/* Review Story Button - Only visible in Todo column */}
              {status === 'Todo' && (
                <div className="mt-3">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleReviewStory} 
                    disabled={isActionLoading}
                    className="border-purple-500 text-purple-600 hover:bg-purple-50 hover:text-purple-700 dark:hover:bg-purple-950"
                  >
                    {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Enhance
                  </Button>
                </div>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        <Separator />

        {/* Tabs Navigation - Hide Chat and Diffs tabs when Done or Archived */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className={`grid w-full ${status === 'Done' || status === 'Archived' ? 'grid-cols-2' : 'grid-cols-4'}`}>
            <TabsTrigger value="detail" className="gap-2">
              <FileText className="w-4 h-4" />
              Detail
            </TabsTrigger>
            {status !== 'Done' && status !== 'Archived' && (
              <TabsTrigger value="chat" className="gap-2">
                <MessageSquare className="w-4 h-4" />
                Chat
              </TabsTrigger>
            )}
            <TabsTrigger value="logs" className="gap-2">
              <ScrollText className="w-4 h-4" />
              Logs
            </TabsTrigger>
            {status !== 'Done' && status !== 'Archived' && (
              <TabsTrigger value="diffs" className="gap-2">
                <GitBranch className="w-4 h-4" />
                Diffs
              </TabsTrigger>
            )}
          </TabsList>

          {/* Detail Tab */}
          <TabsContent value="detail" className="flex-1 overflow-y-auto mt-4 min-h-0">
            <div className="space-y-4 text-sm">
          {/* Description */}
          {card.description && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Mô tả</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{card.description}</p>
            </div>
          )}

          {/* Requirements */}
          {card.requirements && card.requirements.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Requirements</h4>
              <ul className="space-y-1">
                {card.requirements.map((req: string, idx: number) => (
                  <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                    <span className="text-muted-foreground">-</span>
                    <span>{req}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Acceptance Criteria */}
          {card.acceptance_criteria && card.acceptance_criteria.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Acceptance Criteria</h4>
              <ul className="space-y-1">
                {card.acceptance_criteria.map((ac: string, idx: number) => (
                  <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                    <span className="text-muted-foreground">-</span>
                    <span className="whitespace-pre-wrap">{ac}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Status */}
            {card.status && (
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Status</div>
                  <Badge variant="outline" className={`w-fit ${getStatusBadgeColor(card.status)}`}>
                    {formatStatusName(card.status)}
                  </Badge>
                </div>
              </div>
            )}

            {/* Story Points / Estimate */}
            {(card.story_point !== undefined && card.story_point !== null) && (
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Story Points</div>
                  <div className="text-sm font-medium">{card.story_point} SP</div>
                </div>
              </div>
            )}

            {(card.priority !== undefined && card.priority !== null) && (
              <div className="flex items-center gap-2">
                <Flag className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Priority</div>
                  <div className="text-sm font-medium">
                    {card.priority === 1 ? 'High' : 
                     card.priority === 2 ? 'Medium' : 'Low'}
                  </div>
                </div>
              </div>
            )}

            {/* Assignee */}
            {card.assignee_id && (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người thực hiện</div>
                  <div className="text-sm font-medium font-mono">
                    {card.assignee_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {card.type === "EnablerStory" ? "Developer/Infrastructure" : "Developer"}
                  </div>
                </div>
              </div>
            )}

            {/* Reviewer */}
            {card.reviewer_id && (
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người review</div>
                  <div className="text-sm font-medium font-mono">
                    {card.reviewer_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">Tester</div>
                </div>
              </div>
            )}

            {/* Rank */}
            {(card.rank !== undefined && card.rank !== null) && (
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Rank</div>
                  <div className="text-sm font-medium">{card.rank}</div>
                </div>
              </div>
            )}



            {/* Created at */}
            {card.created_at && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Ngày tạo</div>
                  <div className="text-sm font-medium">
                    {new Date(card.created_at).toLocaleDateString('vi-VN')}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Epic */}
          {(card.epic_id || card.epic_title) && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Epic</h4>
              <div className="text-sm text-muted-foreground">
                {card.epic_code && (
                  <Badge 
                    variant="outline" 
                    className="mr-2 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900/30"
                    onClick={() => setSelectedEpic({
                      epic_code: card.epic_code,
                      epic_title: card.epic_title,
                      epic_id: card.epic_id,
                      description: card.epic_description,
                      domain: card.epic_domain,
                    })}
                  >
                    {card.epic_code}
                  </Badge>
                )}
                <span>{card.epic_title || 'None'}</span>
              </div>
            </div>
          )}

          {/* Dependencies */}
          {card.dependencies && card.dependencies.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                Dependencies
              </h4>
              <div className="space-y-2">
                {card.dependencies.map((depId: string, idx: number) => {
                  const depStory = allStories.find(s => s.id === depId)
                  const depTitle = depStory?.content || 'Unknown Story'
                  const depCode = depStory?.story_code || depId.slice(0, 8)
                  return (
                    <div key={idx} className="text-sm text-muted-foreground">
                      {depStory ? (
                        <Badge
                          variant="outline"
                          className="cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30 mr-2"
                          onClick={() => setSelectedDependency(depStory)}
                        >
                          {depCode}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="font-mono">{depCode}</Badge>
                      )}
                      <span>{depTitle}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <Separator />



          {/* TraDS ============= Kanban Hierarchy: Children Display */}
          {card.children && card.children.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">
                Công việc con ({card.children.length})
              </h4>
              <div className="space-y-2">
                {card.children.map((child) => (
                  <div
                    key={child.id}
                    onClick={() => setSelectedChild(child)}
                    className="flex items-center gap-2 p-2 rounded border border-border hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Badge variant="outline" className={getTypeBadgeColor(child.type)}>
                      {formatTypeName(child.type)}
                    </Badge>
                    <span className="text-sm flex-1">{child.content}</span>
                    {child.status && (
                      <Badge variant="outline" className={getStatusBadgeColor(child.status)}>
                        {formatStatusName(child.status)}
                      </Badge>
                    )}
                    {child.story_point !== undefined && child.story_point !== null && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Zap className="w-3 h-3" />
                        {child.story_point} SP
                      </div>
                    )}
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent Info (Legacy) */}
          {card.agentName && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Agent đã xử lý</h4>
              <div className="flex items-center gap-2">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={card.agentAvatar || "/placeholder.svg"} alt={card.agentName} />
                  <AvatarFallback className="bg-primary/10 text-primary text-xs">
                    {card.agentName?.charAt(0) || "A"}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{card.agentName}</span>
              </div>
            </div>
          )}

          {/* Branch */}
          {card.branch && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Branch</h4>
              <code className="text-xs bg-muted px-2 py-1 rounded">{card.branch}</code>
            </div>
          )}

          {/* Subtasks */}
          {card.subtasks && card.subtasks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Subtasks</h4>
              <ul className="space-y-1">
                {card.subtasks.map((subtask, index) => (
                  <li key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                    {subtask}
                  </li>
                ))}
              </ul>
            </div>
          )}

              {/* Result */}
              {card.result && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-foreground">Kết quả</h4>
                    <Button size="sm" variant="outline" onClick={() => onDownloadResult(card)} className="h-7 text-xs">
                      <Download className="w-3 h-3 mr-1" />
                      Tải xuống .md
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground bg-muted p-3 rounded max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">{card.result}</pre>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="flex-1 flex flex-col mt-4 min-h-0 overflow-hidden">
            {/* Chat Header */}
            <div className="flex items-center justify-between pb-3 border-b shrink-0">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold">Story Discussion</h3>
                <Badge variant="outline" className="text-xs">
                  {chatMessages.length} messages
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {chatMessages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearMessages}
                    className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Clear
                  </Button>
                )}
                <div className="flex items-center gap-1.5 text-xs">
                  {isConnected ? (
                    <>
                      <Wifi className="w-3 h-3 text-green-500" />
                      <span className="text-green-600 dark:text-green-400">Live</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3 h-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Connecting...</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Messages Area with Auto-scroll */}
            <Conversation className="flex-1 min-h-0">
              <ConversationContent className="py-2">
                {/* Loading State */}
                {isLoadingMessages && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">Loading messages...</span>
                  </div>
                )}

                {/* Messages - render based on message_type */}
                {!isLoadingMessages && chatMessages.map((msg) => (
                  msg.message_type === 'task' ? (
                    // Task progress - show as Task component
                    <div key={msg.id} className="py-2">
                      <Task defaultOpen={true}>
                        <TaskTrigger 
                          title={msg.author}
                          icon={<Activity className="size-4 text-blue-500" />}
                        />
                        <TaskContent>
                          <TaskItem className="text-foreground">
                            <div className="flex items-start gap-2">
                              <span className="text-xs text-muted-foreground shrink-0">
                                {formatTimestamp(msg.timestamp)}
                              </span>
                              <span className="whitespace-pre-wrap break-words">{msg.content}</span>
                            </div>
                          </TaskItem>
                        </TaskContent>
                      </Task>
                    </div>
                  ) : (
                    // Regular message - show as Message component
                    <Message 
                      key={msg.id} 
                      from={msg.author_type === 'agent' ? 'assistant' : 'user'}
                    >
                      <MessageAvatar
                        name={msg.author}
                        fallback={msg.author_type === 'agent' ? '🤖' : msg.author.charAt(0).toUpperCase()}
                        className={msg.author_type === 'agent' 
                          ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' 
                          : 'bg-primary/10 text-primary'
                        }
                      />
                      <div className="flex flex-col gap-1 max-w-[85%]">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="font-semibold text-foreground">{msg.author}</span>
                          {msg.author_type === 'agent' && (
                            <Badge variant="outline" className="text-[10px] h-4 px-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                              Agent
                            </Badge>
                          )}
                          <span className="text-muted-foreground">{formatTimestamp(msg.timestamp)}</span>
                        </div>
                        <MessageContent
                          className={msg.author_type === 'agent'
                            ? 'bg-blue-500/10 border border-blue-500/20'
                            : ''
                          }
                        >
                          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                        </MessageContent>
                      </div>
                    </Message>
                  )
                ))}

                {/* Thinking Indicator - show when agent is processing */}
                {isAgentThinking && (
                  <Message from="assistant">
                    <MessageAvatar
                      name="Developer"
                      fallback="🤖"
                      className="bg-blue-500/10 text-blue-600 dark:text-blue-400"
                    />
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-semibold text-foreground">Developer</span>
                        <Badge variant="outline" className="text-[10px] h-4 px-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                          Agent
                        </Badge>
                      </div>
                      <MessageContent className="bg-blue-500/10 border border-blue-500/20">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                          <span className="ml-2 text-muted-foreground text-sm">Đang xử lý...</span>
                        </div>
                      </MessageContent>
                    </div>
                  </Message>
                )}

                {/* Empty State - only show when not loading, no messages, and not thinking */}
                {!isLoadingMessages && chatMessages.length === 0 && !isAgentThinking && (
                  <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-12">
                    <MessageSquare className="w-12 h-12 mb-3 opacity-30" />
                    <p className="text-sm font-medium">No messages yet</p>
                    <p className="text-xs mt-1">Start the conversation about this story</p>
                  </div>
                )}
              </ConversationContent>
              <ConversationScrollButton />
            </Conversation>

            {/* Message Input - blended with messages */}
            <div className="shrink-0 px-4 pb-2">
              <PromptInput onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="border-muted-foreground/20">
                <PromptInputTextarea
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="Type a message..."
                />
                <PromptInputToolbar>
                  <PromptInputTools>
                    <PromptInputButton>
                      <Paperclip className="w-4 h-4" />
                    </PromptInputButton>
                    <PromptInputButton>
                      <Smile className="w-4 h-4" />
                    </PromptInputButton>
                  </PromptInputTools>
                  <PromptInputSubmit disabled={!chatMessage.trim()} />
                </PromptInputToolbar>
              </PromptInput>
            </div>
          </TabsContent>

          {/* Logs Tab - Timeline style */}
          <TabsContent value="logs" ref={logsScrollRef} className="flex-1 overflow-y-auto mt-4 min-h-0">
            <div className="space-y-1 px-1 font-mono text-xs">
              {storyLogs.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <ScrollText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No logs yet</p>
                  <p className="text-xs mt-1">Logs will appear here when actions are performed</p>
                </div>
              ) : (
                storyLogs.map((log) => (
                  <div 
                    key={log.id}
                    className={`flex items-start gap-2 px-2 py-1 rounded ${
                      log.level === 'error' ? 'bg-red-500/10 text-red-500' :
                      log.level === 'warning' ? 'bg-yellow-500/10 text-yellow-600' :
                      log.level === 'success' ? 'bg-green-500/10 text-green-600' :
                      log.node === 'restart' ? 'bg-purple-500/10 text-purple-600 font-medium' :
                      log.content?.startsWith('✅') || log.content?.startsWith('🚀') ? 'bg-green-500/10 text-green-600 font-medium' :
                      log.content?.startsWith('❌') ? 'bg-red-500/10 text-red-500 font-medium' :
                      log.content?.startsWith('⚠️') ? 'bg-yellow-500/10 text-yellow-600 font-medium' :
                      'text-muted-foreground hover:bg-muted/50'
                    }`}
                  >
                    <span className="text-muted-foreground/70 shrink-0 w-16">
                      {new Date(log.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    {log.node && (
                      <span className="text-primary/70 shrink-0 w-28 truncate" title={log.node}>
                        [{log.node}]
                      </span>
                    )}
                    <span className="flex-1 break-all">{log.content}</span>
                  </div>
                ))
              )}
            </div>
          </TabsContent>

          {/* Diffs Tab */}
          <TabsContent value="diffs" className="flex-1 overflow-y-auto mt-4 min-h-0">
            <div className="space-y-4">
              {card.worktree_path ? (
                <ErrorBoundary
                  fallback={
                    <div className="text-center text-destructive/70 py-8">
                      <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">Failed to load diffs</p>
                      <p className="text-xs mt-1">Please try refreshing the page</p>
                    </div>
                  }
                >
                  <DiffsView storyId={card.id} onViewInFiles={() => {
                    if (card.worktree_path && onViewFiles) {
                      onOpenChange(false)  // Close dialog
                      onViewFiles(card.worktree_path)  // Navigate to files
                    }
                  }} />
                </ErrorBoundary>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No worktree available</p>
                  <p className="text-xs mt-1">Diffs will appear once the agent starts working</p>
                </div>
              )}
            </div>
          </TabsContent>

        </Tabs>
      </DialogContent>

      {/* TraDS ============= Kanban Hierarchy: Nested dialog for viewing child items */}
      {selectedChild && (
        <TaskDetailModal
          card={selectedChild}
          open={!!selectedChild}
          onOpenChange={() => setSelectedChild(null)}
          onDownloadResult={onDownloadResult}
          allStories={allStories}
          projectId={projectId}
        />
      )}

      {/* Nested dialog for viewing dependency items */}
      {selectedDependency && (
        <TaskDetailModal
          card={selectedDependency}
          open={!!selectedDependency}
          onOpenChange={() => setSelectedDependency(null)}
          onDownloadResult={onDownloadResult}
          allStories={allStories}
          projectId={projectId}
        />
      )}

      {/* Epic detail dialog */}
      {selectedEpic && (
        <Dialog open={!!selectedEpic} onOpenChange={() => setSelectedEpic(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {selectedEpic.epic_code && (
                  <Badge variant="outline" className="">
                    {selectedEpic.epic_code}
                  </Badge>
                )}
                <Badge variant="outline" className="bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20">
                  Epic
                </Badge>
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              {/* Title */}
              <div>
                <h4 className="text-sm font-semibold text-foreground mb-1">Title</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedEpic.epic_title || 'Untitled Epic'}
                </p>
              </div>

              {/* Domain */}
              {selectedEpic.domain && (
                <div>
                  <h4 className="text-sm font-semibold text-foreground mb-1">Domain</h4>
                  <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                    {selectedEpic.domain}
                  </Badge>
                </div>
              )}

              {/* Description */}
              {selectedEpic.description && (
                <div>
                  <h4 className="text-sm font-semibold text-foreground mb-1">Mô tả</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {selectedEpic.description}
                  </p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
      
      {/* Preview Dialog - Fullscreen iframe via backend proxy */}
      {card && (
        <PreviewDialog
          storyId={card.id}
          storyTitle={card.content}
          runningPort={card.running_port}
          open={showPreviewDialog}
          onOpenChange={setShowPreviewDialog}
        />
      )}
    </Dialog>
  )
}
