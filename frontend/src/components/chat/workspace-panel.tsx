
import type React from "react"

import { useState, useRef, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { History, Globe, Code2, LayoutGrid, Pencil, ScrollText, PanelLeftOpen, PanelRightOpen, MessageCircle, Loader2 } from "lucide-react"
import { KanbanBoard } from "./kanban-board"
import { FileExplorer } from "../shared/file-explorer"
import { CodeViewer } from "../shared/code-viewer"
import { AnimatedTooltip } from "../ui/animated-tooltip"
import { AppViewer } from "./app-viewer"
import { DatabaseAgentDetailSheet } from "../agents/database-agent-detail-sheet"
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

export function WorkspacePanel({ chatCollapsed, onExpandChat, kanbanData, projectId, activeTab: wsActiveTab, agentStatuses }: WorkspacePanelProps) {
  const queryClient = useQueryClient()

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

    if (!projectAgents || !projectAgents.length) {
      console.log('[WorkspacePanel] No agents to display')
      return []
    }

    const items = projectAgents.map((agent) => {
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

  // File content state
  const [fileContent, setFileContent] = useState<string>("")
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)

  // Fetch file content when selectedFile changes
  useEffect(() => {
    if (selectedFile && projectId) {
      fetchFileContent(selectedFile)
    } else {
      setFileContent("")
      setFileError(null)
    }
  }, [selectedFile, projectId])

  const fetchFileContent = async (path: string) => {
    if (!projectId) return

    setIsLoadingFile(true)
    setFileError(null)

    try {
      const response = await filesApi.getFileContent(projectId, path)
      setFileContent(response.content)
    } catch (err: any) {
      console.error("Failed to fetch file content:", err)
      setFileError(err.message || "Failed to load file")
      setFileContent("")
    } finally {
      setIsLoadingFile(false)
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
        return (
          <div className="flex-1 overflow-hidden">
            <KanbanBoard kanbanData={kanbanData} projectId={projectId} />
          </div>
        )
      case "file":
        return (
          <div className="flex h-full">
            <div className="w-64 flex-shrink-0">
              <FileExplorer
                projectId={projectId}
                onFileSelect={setSelectedFile}
                selectedFile={selectedFile}
              />
            </div>
            <div className="flex-1">
              {selectedFile ? (
                isLoadingFile ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Loading file...
                  </div>
                ) : fileError ? (
                  <div className="flex items-center justify-center h-full text-destructive">
                    {fileError}
                  </div>
                ) : (
                  <CodeViewer filePath={selectedFile} content={fileContent} />
                )
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  Select a file to view
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
    <div className="flex flex-col h-full bg-background">
      <div className="flex flex-col">

        {/* Toolbar */}
        <div className="flex items-center justify-between px-6 py-2 bg-background">
          <div className="flex items-center gap-3">
            {chatCollapsed && onExpandChat && (
              <button
                onClick={onExpandChat}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-t-lg transition-colors mr-2"
                title="Show chat panel"
              >
                <MessageCircle className="w-4 h-4" /> Chat
              </button>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <History className="w-4 h-4" />
            </Button>

            {isEditingName ? (
              <Input
                ref={inputRef}
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                onBlur={handleSaveName}
                onKeyDown={handleKeyDown}
                className="h-8 text-sm font-medium w-[250px] bg-background border-border"
              />
            ) : (
              <button
                onClick={() => setIsEditingName(true)}
                className="text-sm font-medium text-foreground hover:text-foreground/80 transition-colors flex items-center gap-2 group"
              >
                {projectName}
                <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-10">
            {agentItems.length > 0 ? (
              <AnimatedTooltip items={agentItems} />
            ) : agentsLoading ? (
              <span className="text-xs text-muted-foreground">Loading agents...</span>
            ) : null}
            <Button size="sm" className="h-8 text-xs bg-[#6366f1] hover:bg-[#5558e3]">
              Share
            </Button>
          </div>
        </div>
      </div>
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-2 pt-2 bg-background mb-2">
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
      <div className="border border-3 mb-3 mr-3 shadow-2xs rounded-2xl h-screen overflow-auto">
        {renderView()}
      </div>

      {/* Agent Detail Sheet */}
      <DatabaseAgentDetailSheet
        agent={selectedAgent}
        open={agentDetailOpen}
        onOpenChange={setAgentDetailOpen}
      />
    </div>
  )
}
