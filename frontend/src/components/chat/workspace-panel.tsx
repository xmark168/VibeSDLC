
import type React from "react"

import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { History, Globe, Code2, LayoutGrid, Pencil, ScrollText, PanelLeftOpen, PanelRightOpen, MessageCircle, Loader2, ChevronsRight, Download, FileText } from "lucide-react"
import { KanbanBoard } from "./kanban-board"
import { FileExplorer } from "../shared/file-explorer"
import { CodeViewer } from "../shared/code-viewer"
import { AnimatedTooltip } from "../ui/animated-tooltip"
import { AppViewer } from "./app-viewer"
import { AgentPopup } from "../agents/agent-popup"
import { useProjectAgents } from "@/queries/agents"
import { useQueryClient } from "@tanstack/react-query"
import type { AgentPublic } from "@/client/types.gen"
import { filesApi } from "@/apis/files"

type WorkspaceView = "app-preview" | "kanban" | "file" | "loggings"
interface Tab {
  id: string
  view: WorkspaceView
  label: string
}

interface WorkspacePanelProps {
  chatCollapsed?: boolean
  onExpandChat?: () => void
  kanbanData?: any
  projectId?: string
  activeTab?: string | null
  agentStatuses?: Map<string, { status: string; lastUpdate: string }> // Real-time agent statuses from WebSocket
  selectedArtifactId?: string | null
  initialSelectedFile?: string | null
  onResize?: (delta: number) => void
  onMessageAgent?: (agentName: string) => void // Callback to @mention agent in chat
}

// Generate avatar URL from agent human_name using DiceBear API
const generateAvatarUrl = (name: string): string => {
  const initials = name
    .split(' ')
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
  // Using DiceBear API for initials-based avatars
  return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}&chars=2&backgroundColor=6366f1`
}

// Map role_type to user-friendly designation
const getRoleDesignation = (roleType: string): string => {
  const roleMap: Record<string, string> = {
    team_leader: "Team Leader",
    business_analyst: "Business Analyst",
    developer: "Developer",
    tester: "Tester",
  }
  return roleMap[roleType] || roleType
}

export function WorkspacePanel({ chatCollapsed, onExpandChat, kanbanData, projectId, activeTab: wsActiveTab, agentStatuses, selectedArtifactId, onResize, initialSelectedFile, onMessageAgent }: WorkspacePanelProps) {
  const queryClient = useQueryClient()

  // Resize handle state - use refs to avoid re-renders during drag
  const isDraggingRef = useRef(false)
  const startXRef = useRef(0)
  const rafIdRef = useRef<number | null>(null)
  const pendingDeltaRef = useRef(0)
  const onResizeRef = useRef(onResize)

  // Keep onResize ref updated
  useEffect(() => {
    onResizeRef.current = onResize
  }, [onResize])

  useEffect(() => {
    const applyResize = () => {
      if (pendingDeltaRef.current !== 0 && onResizeRef.current) {
        onResizeRef.current(pendingDeltaRef.current)
        pendingDeltaRef.current = 0
      }
      rafIdRef.current = null
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return
      e.preventDefault()

      // Accumulate delta
      const delta = e.clientX - startXRef.current
      startXRef.current = e.clientX
      pendingDeltaRef.current += delta

      // Use requestAnimationFrame for smooth updates
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(applyResize)
      }
    }

    const handleMouseUp = () => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false
        document.body.style.userSelect = ""
        document.body.style.cursor = ""

        // Apply any remaining delta
        if (rafIdRef.current !== null) {
          cancelAnimationFrame(rafIdRef.current)
          rafIdRef.current = null
        }
        if (pendingDeltaRef.current !== 0 && onResizeRef.current) {
          onResizeRef.current(pendingDeltaRef.current)
          pendingDeltaRef.current = 0
        }
      }
    }

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)

    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
      }
    }
  }, [])

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    if (!onResizeRef.current) return
    e.preventDefault()
    isDraggingRef.current = true
    startXRef.current = e.clientX
    pendingDeltaRef.current = 0
    document.body.style.userSelect = "none"
    document.body.style.cursor = "col-resize"
  }, [])

  // Fetch project agents from database
  const { data: projectAgents, isLoading: agentsLoading } = useProjectAgents(projectId || "", {
    enabled: !!projectId,
  })

  // State for agent detail sheet
  const [selectedAgent, setSelectedAgent] = useState<AgentPublic | null>(null)
  const [agentDetailOpen, setAgentDetailOpen] = useState(false)

  // Transform agents for AnimatedTooltip component
  const agentItems = useMemo(() => {
    console.log('[WorkspacePanel] Project agents data:', projectAgents)
    console.log('[WorkspacePanel] Agents loading:', agentsLoading)
    console.log('[WorkspacePanel] WebSocket agent statuses:', agentStatuses)

    // Handle both { data: [...] } and direct array response
    const agentsList: AgentPublic[] = Array.isArray(projectAgents) 
      ? projectAgents 
      : (projectAgents?.data || [])

    if (!agentsList.length) {
      console.log('[WorkspacePanel] No agents to display')
      return []
    }

    const items = agentsList.map((agent: AgentPublic) => {
      // Lấy status từ WebSocket (real-time), fallback về database nếu chưa có
      const wsStatus = agentStatuses?.get(agent.human_name)
      const displayStatus = wsStatus?.status || agent.status || 'idle'

      console.log(`[WorkspacePanel] Agent ${agent.human_name}: WS status=${wsStatus?.status}, DB status=${agent.status}, Display=${displayStatus}`)

      return {
        id: agent.id,
        name: agent.human_name, // Use human name like "Mike"
        designation: getRoleDesignation(agent.role_type),
        image: generateAvatarUrl(agent.human_name),
        status: displayStatus, // Use WebSocket status (real-time) or fallback to DB
        onClick: () => {
          // Open detail sheet when agent is clicked
          setSelectedAgent(agent)
          setAgentDetailOpen(true)
        },
      }
    })

    console.log('[WorkspacePanel] Agent items for AnimatedTooltip:', items)
    return items
  }, [projectAgents, agentsLoading, agentStatuses]) // Include agentStatuses in dependencies

  const [tabs, setTabs] = useState<Tab[]>([
    { id: "tab-1", view: "app-preview", label: "App Preview" },
    { id: "tab-2", view: "kanban", label: "Kanban" },
    { id: "tab-3", view: "file", label: "File" },
    { id: "tab-4", view: "loggings", label: "Loggings" },
  ])
  const [activeTabId, setActiveTabId] = useState("tab-1")

  // Auto-switch tab when wsActiveTab changes from WebSocket
  useEffect(() => {
    if (wsActiveTab) {
      const tabMap: Record<string, string> = {
        'kanban': 'tab-2',
        'app-preview': 'tab-1',
        'file': 'tab-3',
        'loggings': 'tab-4',
      }
      const targetTabId = tabMap[wsActiveTab]
      if (targetTabId) {
        console.log('[WorkspacePanel] Auto-switching to tab:', wsActiveTab, targetTabId)
        setActiveTabId(targetTabId)
      }
    }
  }, [wsActiveTab])
  const [projectName, setProjectName] = useState("Website sobre camisetas")
  const [isEditingName, setIsEditingName] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [selectedWorktree, setSelectedWorktree] = useState<string | undefined>(undefined)

  // Update selectedFile when initialSelectedFile changes from parent
  useEffect(() => {
    if (initialSelectedFile) {
      setSelectedFile(initialSelectedFile)
    }
  }, [initialSelectedFile])

  // File content state
  const [fileContent, setFileContent] = useState<string>("")
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [isFileBinary, setIsFileBinary] = useState(false)

  // Artifact state
  const [selectedArtifact, setSelectedArtifact] = useState<any | null>(null)
  const [isLoadingArtifact, setIsLoadingArtifact] = useState(false)

  // Fetch artifact when selectedArtifactId changes
  useEffect(() => {
    if (selectedArtifactId && projectId) {
      fetchArtifact(selectedArtifactId)
    } else {
      setSelectedArtifact(null)
    }
  }, [selectedArtifactId, projectId])

  const fetchArtifact = async (artifactId: string) => {
    if (!projectId) return

    setIsLoadingArtifact(true)

    try {
      const { artifactsApi } = await import('@/apis/artifacts')
      const artifact = await artifactsApi.getArtifact(artifactId)
      setSelectedArtifact(artifact)
      console.log('[WorkspacePanel] Loaded artifact:', artifact)
    } catch (err: any) {
      console.error('Failed to fetch artifact:', err)
      setSelectedArtifact(null)
    } finally {
      setIsLoadingArtifact(false)
    }
  }

  // Fetch file content when selectedFile changes
  useEffect(() => {
    if (selectedFile && projectId) {
      fetchFileContent(selectedFile, selectedWorktree)
    } else {
      setFileContent("")
      setFileError(null)
      setIsFileBinary(false)
    }
  }, [selectedFile, projectId, selectedWorktree])

  const fetchFileContent = async (path: string, worktree?: string) => {
    if (!projectId) return

    setIsLoadingFile(true)
    setFileError(null)
    setIsFileBinary(false)

    try {
      const response = await filesApi.getFileContent(projectId, path, worktree)
      setFileContent(response.content)
      setIsFileBinary(response.is_binary || false)
    } catch (err: any) {
      console.error("Failed to fetch file content:", err)
      setFileError(err.message || "Failed to load file")
      setFileContent("")
    } finally {
      setIsLoadingFile(false)
    }
  }
  
  // Download file from uploads folder
  const handleDownloadFile = async () => {
    if (!projectId || !selectedFile) return
    
    try {
      // Get token for auth
      const token = localStorage.getItem("access_token")
      const baseUrl = import.meta.env.VITE_API_URL || ''
      
      // Fetch file as blob
      const response = await fetch(
        `${baseUrl}/api/v1/projects/${projectId}/files/download?path=${encodeURIComponent(selectedFile)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      
      if (!response.ok) {
        throw new Error('Download failed')
      }
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      // Get filename from path
      const filename = selectedFile.split('/').pop() || 'download'
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Không thể tải file. Vui lòng thử lại.')
    }
  }

  useEffect(() => {
    if (isEditingName && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditingName])

  const handleSaveName = () => {
    setIsEditingName(false)
    if (projectName.trim() === "") {
      setProjectName("Untitled Project")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSaveName()
    } else if (e.key === "Escape") {
      setIsEditingName(false)
    }
  }

  const getViewIcon = (view: WorkspaceView) => {
    switch (view) {
      case "app-preview":
        return <Globe className="w-3.5 h-3.5" />
      case "kanban":
        return <LayoutGrid className="w-3.5 h-3.5" />
      case "file":
        return <Code2 className="w-3.5 h-3.5" />
      case "loggings":
        return <ScrollText className="w-3.5 h-3.5" />
      default:
        return <Globe className="w-3.5 h-3.5" />
    }
  }

  const activeTab = tabs.find((tab) => tab.id === activeTabId)
  const activeView = activeTab?.view || "app-preview"

  const renderView = () => {
    switch (activeView) {
      case "app-preview":
        return (
          <AppViewer />
        )
      case "kanban":
        // KanbanBoard is rendered separately to keep it always mounted
        return null
      case "file":
        return (
          <div className="flex h-full">
            <div className="w-64 flex-shrink-0">
              <FileExplorer
                projectId={projectId}
                onFileSelect={(path, worktree) => {
                  setSelectedFile(path)
                  setSelectedWorktree(worktree)
                }}
                selectedFile={selectedFile}
                initialWorktree={selectedWorktree}
              />
            </div>
            <div className="flex-1">
              {selectedArtifact ? (
                isLoadingArtifact ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Loading artifact...
                  </div>
                ) : (
                  (() => {
                    const { ArtifactViewer } = require('./ArtifactViewer')
                    return (
                      <ArtifactViewer
                        artifact={selectedArtifact}
                        onClose={() => setSelectedArtifact(null)}
                      />
                    )
                  })()
                )
              ) : selectedFile ? (
                isLoadingFile ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Loading file...
                  </div>
                ) : fileError ? (
                  <div className="flex items-center justify-center h-full text-destructive">
                    {fileError}
                  </div>
                ) : isFileBinary ? (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
                    <div className="flex items-center justify-center w-16 h-16 bg-muted rounded-lg">
                      <FileText className="w-8 h-8" />
                    </div>
                    <div className="text-center">
                      <p className="font-medium text-foreground">{selectedFile.split('/').pop()}</p>
                      <p className="text-sm mt-1">Binary file - cannot preview</p>
                    </div>
                    <Button onClick={handleDownloadFile} className="gap-2">
                      <Download className="w-4 h-4" />
                      Download File
                    </Button>
                  </div>
                ) : (
                  <CodeViewer filePath={selectedFile} content={fileContent} />
                )
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  {selectedArtifactId ? 'Loading artifact...' : 'Select a file or artifact to view'}
                </div>
              )}
            </div>
          </div>
        )
      case "loggings":
        return (
          <>

          </>
        )
      default:
        return null
    }
  }


  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Left resize border */}
      {onResize && (
        <div
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/20 transition-colors z-10"
          onMouseDown={handleResizeStart}
        />
      )}
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-2 pt-2 bg-background mb-2 justify-between">
        <div className="flex gap-1 items-center">
          {/* Show expand chat button when chat is collapsed */}
          {chatCollapsed && onExpandChat && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onExpandChat}
              className="h-8 px-2 mr-1"
              title="Mở lại Chat"
            >
              <ChevronsRight className="w-4 h-4" />
            </Button>
          )}
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              className={`rounded-md group flex items-center gap-2 px-3 py-1.5 text-sm font-medium transition-colors ${activeTabId === tab.id
                ? "bg-muted text-foreground"
                : "bg-transparent text-muted-foreground hover:bg-muted/50"
                }`}
            >
              {getViewIcon(tab.view)}
              <span className="max-w-[120px] truncate">{tab.label}</span>
            </button>
          ))}
        </div>
        <div className="flex gap-6 items-center">

          <div>
            {agentItems.length > 0 ? (
              <AnimatedTooltip items={agentItems} />
            ) : agentsLoading ? (
              <span className="text-xs text-muted-foreground">Loading agents...</span>
            ) : null}

          </div>
          <div>
            <Button size="sm" className="h-8 text-xs bg-[#6366f1] hover:bg-[#5558e3]">
              Public
            </Button>
          </div>
        </div>
      </div>
      <div className="border border-3 mb-3 mr-3 shadow-2xs rounded-2xl flex-1 min-h-0 overflow-hidden">
        <div className="h-full w-full overflow-auto">
          {/* Keep KanbanBoard always mounted for real-time updates */}
          <div className={activeView === "kanban" ? "h-full" : "hidden"}>
            <div className="flex-1 overflow-hidden h-full">
              <KanbanBoard 
                kanbanData={kanbanData} 
                projectId={projectId}
                onViewFiles={(worktreePath) => {
                  setSelectedWorktree(worktreePath)
                  // Find the file tab and switch to it
                  const fileTab = tabs.find(t => t.view === "file")
                  if (fileTab) setActiveTabId(fileTab.id)
                }}
              />
            </div>
          </div>
          {/* Other views render conditionally */}
          {activeView !== "kanban" && renderView()}
        </div>
      </div>

      {/* Agent Popup */}
      <AgentPopup
        agent={selectedAgent}
        open={agentDetailOpen}
        onOpenChange={setAgentDetailOpen}
        onMessage={onMessageAgent}
      />
    </div>
  )
}
