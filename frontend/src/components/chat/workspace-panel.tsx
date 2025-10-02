
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { History, Globe, Code2, ExternalLink, LayoutGrid, Pencil, ScrollText, Plus, X } from "lucide-react"
import { KanbanBoard } from "./kanban-board"

type WorkspaceView = "app-preview" | "kanban" | "file" | "loggings"

interface Tab {
  id: string
  view: WorkspaceView
  label: string
}

export function WorkspacePanel() {
  const [tabs, setTabs] = useState<Tab[]>([
    { id: "tab-1", view: "app-preview", label: "App Preview" },
    { id: "tab-2", view: "kanban", label: "Kanban" },
    { id: "tab-3", view: "file", label: "File" },
    { id: "tab-4", view: "loggings", label: "Loggings" },
  ])
  const [activeTabId, setActiveTabId] = useState("tab-1")
  const [projectName, setProjectName] = useState("Website sobre camisetas")
  const [isEditingName, setIsEditingName] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

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

  const handleAddTab = () => {
    const newTab: Tab = {
      id: `tab-${Date.now()}`,
      view: "app-preview",
      label: "New Tab",
    }
    setTabs([...tabs, newTab])
    setActiveTabId(newTab.id)
  }

  const handleCloseTab = (tabId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (tabs.length === 1) return // Don't close the last tab

    const tabIndex = tabs.findIndex((t) => t.id === tabId)
    const newTabs = tabs.filter((t) => t.id !== tabId)
    setTabs(newTabs)

    // If closing active tab, switch to adjacent tab
    if (activeTabId === tabId) {
      const newActiveTab = newTabs[Math.max(0, tabIndex - 1)]
      setActiveTabId(newActiveTab.id)
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
          <div className="flex-1 overflow-auto bg-background">
            <div className="max-w-6xl mx-auto p-12">
              <div className="text-center space-y-6">
                <div className="flex justify-between items-start mb-8">
                  <h1 className="text-3xl font-bold text-foreground">Costume T-Shirt Shop</h1>
                  <Button variant="outline" className="text-sm bg-transparent">
                    Browse Catalog
                  </Button>
                </div>

                <div className="space-y-4">
                  <h2 className="text-6xl font-bold text-primary leading-tight">Wear the character.</h2>
                  <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                    Premium costume-themed T-shirts. Find your character and wear the look.
                  </p>
                </div>

                <div className="flex gap-4 justify-center mt-8">
                  <Button className="px-8 py-6 text-lg">Shop Now</Button>
                  <Button variant="outline" className="px-8 py-6 text-lg bg-transparent">
                    View Cart
                  </Button>
                </div>

                <div className="mt-16">
                  <h3 className="text-2xl font-bold text-foreground mb-8">Featured Tees</h3>
                  <div className="bg-card rounded-lg overflow-hidden border">
                    <img
                      src="/abstract-infinity-symbol-design-in-white-on-black-.jpg"
                      alt="Featured design"
                      className="w-full h-[400px] object-cover"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      case "kanban":
        return <KanbanBoard />
      case "file":
        return (
          <div className="flex-1 overflow-auto bg-[#1e1e1e] text-[#d4d4d4] font-mono">
            <div className="p-4">
              <div className="text-xs text-[#858585] mb-2">app/page.tsx</div>
              <pre className="text-sm leading-relaxed">
                <code>
                  {`export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold">
          Welcome to Next.js!
        </h1>
      </div>
    </main>
  )
}`}
                </code>
              </pre>
            </div>
          </div>
        )
      case "loggings":
        return (
          <div className="flex-1 overflow-auto bg-[#1a1a1a] text-[#d4d4d4] font-mono">
            <div className="p-4 space-y-2">
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:45]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Application started successfully</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:46]</span> <span className="text-[#60a5fa]">DEBUG</span>{" "}
                <span className="text-[#d4d4d4]">Loading configuration from env</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:47]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Database connection established</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:48]</span> <span className="text-[#fbbf24]">WARN</span>{" "}
                <span className="text-[#d4d4d4]">Deprecated API usage detected in module auth.ts</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:49]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Server listening on port 3000</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:50]</span> <span className="text-[#ef4444]">ERROR</span>{" "}
                <span className="text-[#d4d4d4]">Failed to load user preferences: Network timeout</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:51]</span> <span className="text-[#60a5fa]">DEBUG</span>{" "}
                <span className="text-[#d4d4d4]">Retrying connection attempt 1/3</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:52]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">User preferences loaded successfully</span>
              </div>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      <div className="flex flex-col border-b border-border">
        {/* Tab bar */}
        <div className="flex items-center gap-0 px-2 pt-2 bg-muted/30">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              className={`group flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all relative ${
                activeTabId === tab.id
                  ? "bg-background text-foreground rounded-t-lg border-t border-l border-r border-border"
                  : "bg-transparent text-muted-foreground hover:bg-muted/50 rounded-t-lg"
              }`}
              style={{
                marginBottom: activeTabId === tab.id ? "-1px" : "0",
              }}
            >
              {getViewIcon(tab.view)}
              <span className="max-w-[120px] truncate">{tab.label}</span>
              {tabs.length > 1 && (
                <button
                  onClick={(e) => handleCloseTab(tab.id, e)}
                  className="ml-1 opacity-0 group-hover:opacity-100 hover:bg-muted rounded p-0.5 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </button>
          ))}
          <button
            onClick={handleAddTab}
            className="flex items-center justify-center w-8 h-8 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-t-lg transition-colors ml-1"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between px-6 py-2 bg-background">
          <div className="flex items-center gap-3">
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

          <div className="flex items-center gap-2">
            <div className="flex -space-x-2">
              <div className="w-7 h-7 rounded-full bg-[#f59e0b] border-2 border-background flex items-center justify-center">
                <span className="text-xs text-white">😊</span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#3b82f6] border-2 border-background flex items-center justify-center">
                <span className="text-xs text-white">💬</span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#8b5cf6] border-2 border-background flex items-center justify-center">
                <span className="text-xs text-white">🎨</span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#10b981] border-2 border-background flex items-center justify-center">
                <span className="text-xs text-white">🤖</span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#ec4899] border-2 border-background flex items-center justify-center">
                <span className="text-xs text-white">✨</span>
              </div>
            </div>
            <Button size="sm" className="h-8 text-xs bg-[#6366f1] hover:bg-[#5558e3]">
              Share
            </Button>
          </div>
        </div>
      </div>

      {renderView()}
    </div>
  )
}
