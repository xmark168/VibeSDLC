
import { Download, Zap, User, Users, Flag, Calendar, ChevronRight, MessageSquare, FileText, ScrollText, Send, Paperclip, Smile, Link2, ExternalLink, Loader2, Wifi, WifiOff, Square, RotateCcw, GitBranch, Plus, Minus, FileCode, Pause, Play } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { KanbanCardData } from "./kanban-card"
import { useState, useRef, useEffect, useCallback } from "react"
import { useStoryWebSocket } from "@/hooks/useStoryWebSocket"

// DiffsView component for showing git diffs
function DiffsView({ storyId }: { storyId: string }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [diffs, setDiffs] = useState<{ files: { status: string; filename: string }[]; file_count: number; diff: string } | null>(null)
  
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
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* File list */}
      <div className="border rounded-lg">
        <div className="px-3 py-2 bg-muted/50 border-b text-xs font-medium text-muted-foreground flex items-center gap-2">
          <FileCode className="w-4 h-4" />
          {diffs.file_count} files changed
        </div>
        <div className="divide-y">
          {diffs.files.map((file, idx) => (
            <div key={idx} className="px-3 py-2 text-xs flex items-center gap-2 hover:bg-muted/30">
              {file.status === 'A' && <Plus className="w-3 h-3 text-green-500" />}
              {file.status === 'M' && <FileText className="w-3 h-3 text-amber-500" />}
              {file.status === 'D' && <Minus className="w-3 h-3 text-red-500" />}
              <span className="font-mono truncate">{file.filename}</span>
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

interface TaskDetailModalProps {
  card: KanbanCardData | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadResult: (card: KanbanCardData) => void
  allStories?: KanbanCardData[]  // For resolving dependency titles
  projectId?: string  // For WebSocket connection
}

// Mock chat messages type
interface ChatMessage {
  id: string
  author: string
  author_type: 'user' | 'agent'
  content: string
  timestamp: string
  avatar?: string
}

// Epic info for popup
interface EpicInfo {
  epic_code?: string
  epic_title?: string
  epic_id?: string
  description?: string
  domain?: string
}

export function TaskDetailModal({ card, open, onOpenChange, onDownloadResult, allStories = [], projectId }: TaskDetailModalProps) {
  const [selectedChild, setSelectedChild] = useState<KanbanCardData | null>(null)
  const [selectedDependency, setSelectedDependency] = useState<KanbanCardData | null>(null)
  const [selectedEpic, setSelectedEpic] = useState<EpicInfo | null>(null)
  const [localAgentState, setLocalAgentState] = useState<string | null>(null)
  
  // Sync local agent state with card prop
  useEffect(() => {
    if (card?.agent_state) {
      setLocalAgentState(card.agent_state)
    }
  }, [card?.agent_state])
  
  // Listen for story state changes via WebSocket
  useEffect(() => {
    const handleStoryStateChanged = (event: CustomEvent) => {
      if (event.detail.story_id === card?.id) {
        setLocalAgentState(event.detail.agent_state)
      }
    }
    
    window.addEventListener('story-state-changed', handleStoryStateChanged as EventListener)
    return () => {
      window.removeEventListener('story-state-changed', handleStoryStateChanged as EventListener)
    }
  }, [card?.id])
  
  // Use local state for agent_state display
  const agentState = localAgentState || card?.agent_state
  
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
  const chatScrollRef = useRef<HTMLDivElement>(null)
  const token = getToken()

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
  const { messages: chatMessages, isConnected } = useStoryWebSocket(
    open ? card?.id ?? null : null,
    projectId ?? null,
    token ?? undefined,
    initialMessages
  )

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatScrollRef.current && activeTab === 'chat') {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [chatMessages, activeTab])

  if (!card) return null

  const handleSendMessage = () => {
    if (!chatMessage.trim()) return

    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      author: 'Current User',
      author_type: 'user',
      content: chatMessage,
      timestamp: new Date().toISOString(),
    }

    setChatMessages(prev => [...prev, newMessage])
    setChatMessage("")
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
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
                          agentState === 'processing' ? 'bg-primary animate-pulse' :
                          agentState === 'paused' ? 'bg-amber-500' :
                          agentState === 'finished' ? 'bg-green-500' :
                          agentState === 'canceled' ? 'bg-destructive' :
                          'bg-muted-foreground'
                        }`}></span>
                        {agentState === 'processing' ? 'Processing' :
                         agentState === 'paused' ? 'Paused' :
                         agentState === 'finished' ? 'Finished' :
                         agentState === 'canceled' ? 'Canceled' : 'Pending'}
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

              {/* Action Buttons */}
              {agentState && (
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  {/* Dev Server Toggle */}
                  {agentState === 'finished' && card.worktree_path && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={card.running_port ? handleStopDevServer : handleStartDevServer}
                      disabled={isActionLoading}
                    >
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 
                       card.running_port ? <Square className="w-4 h-4" /> : <ExternalLink className="w-4 h-4" />}
                      {card.running_port ? 'Stop Server' : 'Dev Server'}
                    </Button>
                  )}
                  
                  {/* Preview Link */}
                  {card.running_port && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={`http://localhost:${card.running_port}`} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4" />
                        Preview
                      </a>
                    </Button>
                  )}

                  {/* Pause when processing */}
                  {agentState === 'processing' && (
                    <Button variant="outline" size="sm" onClick={handlePauseTask} disabled={isActionLoading}>
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pause className="w-4 h-4" />}
                      Tạm dừng
                    </Button>
                  )}
                  
                  {/* Resume when paused */}
                  {agentState === 'paused' && (
                    <Button variant="default" size="sm" onClick={handleResumeTask} disabled={isActionLoading}>
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      Tiếp tục
                    </Button>
                  )}
                  
                  {/* Cancel when processing or paused */}
                  {(agentState === 'pending' || agentState === 'processing' || agentState === 'paused') && (
                    <Button variant="destructive" size="sm" className="bg-red-600 hover:bg-red-700 text-white" onClick={handleCancelTask} disabled={isActionLoading}>
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
                      Hủy
                    </Button>
                  )}
                  
                  {/* Restart when canceled or finished */}
                  {(agentState === 'canceled' || agentState === 'finished') && (
                    <Button variant="default" size="sm" onClick={handleRestartTask} disabled={isActionLoading}>
                      {isActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                      Chạy lại
                    </Button>
                  )}
                </div>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        <Separator />

        {/* Tabs Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="detail" className="gap-2">
              <FileText className="w-4 h-4" />
              Detail
            </TabsTrigger>
            <TabsTrigger value="chat" className="gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat
            </TabsTrigger>
            <TabsTrigger value="logs" className="gap-2">
              <ScrollText className="w-4 h-4" />
              Logs
            </TabsTrigger>
            <TabsTrigger value="diffs" className="gap-2">
              <FileText className="w-4 h-4" />
              Diffs
            </TabsTrigger>
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
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold">Story Discussion</h3>
                <Badge variant="outline" className="text-xs">
                  {chatMessages.length} messages
                </Badge>
              </div>
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

            {/* Messages Area */}
            <div
              ref={chatScrollRef}
              className="flex-1 overflow-y-auto py-4 space-y-4"
            >
              {/* Loading State */}
              {isLoadingMessages && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading messages...</span>
                </div>
              )}

              {!isLoadingMessages && chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-start gap-3 ${
                    msg.author_type === 'user' ? 'flex-row' : 'flex-row'
                  }`}
                >
                  {/* Avatar */}
                  <Avatar className="w-8 h-8 shrink-0">
                    {msg.author_type === 'agent' ? (
                      <AvatarFallback className="bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs">
                        🤖
                      </AvatarFallback>
                    ) : (
                      <AvatarFallback className="bg-primary/10 text-primary text-xs">
                        {msg.author.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    )}
                  </Avatar>

                  {/* Message Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-xs font-semibold text-foreground">
                        {msg.author}
                      </span>
                      {msg.author_type === 'agent' && (
                        <Badge variant="outline" className="text-[10px] h-4 px-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                          Agent
                        </Badge>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        {formatTimestamp(msg.timestamp)}
                      </span>
                    </div>
                    <div className={`
                      text-sm rounded-lg px-3 py-2 inline-block max-w-full
                      ${msg.author_type === 'agent'
                        ? 'bg-blue-500/10 text-foreground border border-blue-500/20'
                        : 'bg-muted text-foreground'
                      }
                    `}>
                      <p className="whitespace-pre-wrap wrap-break-word">{msg.content}</p>
                    </div>
                  </div>
                </div>
              ))}

              {/* Empty State */}
              {!isLoadingMessages && chatMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-12">
                  <MessageSquare className="w-12 h-12 mb-3 opacity-30" />
                  <p className="text-sm font-medium">No messages yet</p>
                  <p className="text-xs mt-1">Start the conversation about this story</p>
                </div>
              )}
            </div>

            {/* Message Input */}
            <div className="pt-3 border-t">
              <div className="flex items-end gap-2">
                <div className="flex-1 relative">
                  <Textarea
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type a message... (Shift+Enter for new line)"
                    className="min-h-[60px] max-h-[120px] resize-none pr-20 text-sm"
                  />
                  <div className="absolute right-2 bottom-2 flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 hover:bg-muted"
                    >
                      <Paperclip className="w-4 h-4 text-muted-foreground" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 hover:bg-muted"
                    >
                      <Smile className="w-4 h-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!chatMessage.trim()}
                  size="sm"
                  className="h-[60px] px-4"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-[10px] text-muted-foreground mt-1.5">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="flex-1 overflow-y-auto mt-4 min-h-0">
            <div className="space-y-4">
              <div className="text-center text-muted-foreground py-8">
                <ScrollText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Activity logs coming soon...</p>
                <p className="text-xs mt-1">View all activities and changes for this story</p>
              </div>
            </div>
          </TabsContent>

          {/* Diffs Tab */}
          <TabsContent value="diffs" className="flex-1 overflow-y-auto mt-4 min-h-0">
            <div className="space-y-4">
              {card.worktree_path ? (
                <DiffsView storyId={card.id} />
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
    </Dialog>
  )
}
