
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { History, Globe, Code2, LayoutGrid, Pencil, ScrollText, PanelLeftOpen, PanelRightOpen, MessageCircle } from "lucide-react"
import { KanbanBoard } from "./kanban-board"
import { FileExplorer } from "../shared/file-explorer"
import { CodeViewer } from "../shared/code-viewer"
import { AnimatedTooltip } from "../ui/animated-tooltip"
import { AppViewer } from "./app-viewer"

import { useQueryClient } from "@tanstack/react-query"
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
}

const agent = [
  {
    id: 1,
    name: "John Doe",
    designation: "Product Owner",
    image:
      "https://images.unsplash.com/photo-1599566150163-29194dcaad36?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=3387&q=80",
  },
  {
    id: 2,
    name: "Robert Johnson",
    designation: "Scrum Master",
    image:
      "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8YXZhdGFyfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60",
  },
  {
    id: 3,
    name: "Jane Smith",
    designation: "Developer",
    image:
      "https://images.unsplash.com/photo-1580489944761-15a19d654956?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8YXZhdGFyfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60",
  },
  {
    id: 4,
    name: "Emily Davis",
    designation: "Designer",
    image:
      "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fGF2YXRhcnxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=800&q=60",
  },
  {
    id: 5,
    name: "Tyler Durden",
    designation: "Tester",
    image:
      "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=3540&q=80",
  },
];


export function WorkspacePanel({ chatCollapsed, onExpandChat, kanbanData, projectId, activeTab: wsActiveTab }: WorkspacePanelProps) {
  const queryClient = useQueryClient()

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
  const [selectedFile, setSelectedFile] = useState<string | null>("components/sidebar.tsx")
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
              <FileExplorer onFileSelect={setSelectedFile} selectedFile={selectedFile} />
            </div>
            <div className="flex-1">
              {selectedFile ? (
                <CodeViewer filePath={selectedFile} content={getFileContent(selectedFile)} />
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

  const getFileContent = (path: string): string => {
    // Mock file contents - in a real app, this would fetch from an API
    const contents: Record<string, string> = {
      "components/sidebar.tsx": `"use client"

import { Button } from "@/components/ui/button"
import { Menu, Plus, Sparkles, ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from "@/lib/utils"
import { useState } from "react"

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const [myChatsExpanded, setMyChatsExpanded] = useState(true)

  const chats = [
    { id: "1", title: "ádf", active: false },
    { id: "2", title: "Website sobre camisetas", active: true },
  ]

  return (
    <div className={cn(
      "flex flex-col bg-sidebar border-r border-sidebar-border",
      collapsed ? "absolute -translate-x-full" : "relative translate-x-0"
    )}>
      {/* Sidebar content */}
    </div>
  )
}`,
      "app/page.tsx": `"use client"

import { useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatPanel } from "@/components/chat-panel"
import { WorkspacePanel } from "@/components/workspace-panel"

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <ChatPanel />
      <WorkspacePanel />
    </div>
  )
}`,
      "package.json": `{
  "name": "multi-agent-dev-platform",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "15.1.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}`,
    }

    return contents[path] || `// File: ${path}\n// Content not available`
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
            <AnimatedTooltip items={agent} />
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
    </div>
  )
}
