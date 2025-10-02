
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { History, Globe, Code2, ExternalLink, Terminal, FolderOpen, LayoutGrid, Pencil, Plus } from "lucide-react"
import { KanbanBoard } from "./kanban-board"

type WorkspaceView = "app-viewer" | "editor" | "terminal" | "file" | "planner" | "kanban"

export function WorkspacePanel() {
  const [activeView, setActiveView] = useState<WorkspaceView>("kanban")
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

  const getViewName = () => {
    switch (activeView) {
      case "app-viewer":
        return "Preview"
      case "editor":
        return "Editor"
      case "terminal":
        return "Terminal"
      case "file":
        return "File"
      case "planner":
        return "Planner"
      case "kanban":
        return "Kanban"
      default:
        return "Kanban"
    }
  }

  const views: Array<{ id: WorkspaceView; icon: React.ReactNode; label: string }> = [
    { id: "app-viewer", icon: <Globe className="w-4 h-4" />, label: "Preview" },
    { id: "editor", icon: <Code2 className="w-4 h-4" />, label: "Editor" },
    { id: "terminal", icon: <Terminal className="w-4 h-4" />, label: "Terminal" },
    { id: "file", icon: <FolderOpen className="w-4 h-4" />, label: "File" },
    { id: "planner", icon: <LayoutGrid className="w-4 h-4" />, label: "Planner" },
    { id: "kanban", icon: <LayoutGrid className="w-4 h-4" />, label: "Kanban" },
  ]

  const renderView = () => {
    switch (activeView) {
      case "kanban":
        return <KanbanBoard />
      case "app-viewer":
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
      case "editor":
        return (
          <div className="flex-1 flex items-center justify-center bg-muted">
            <div className="text-center">
              <Code2 className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">Code Editor View</p>
            </div>
          </div>
        )
      case "terminal":
        return (
          <div className="flex-1 flex items-center justify-center bg-muted">
            <div className="text-center">
              <Terminal className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">Terminal View</p>
            </div>
          </div>
        )
      case "file":
        return (
          <div className="flex-1 flex items-center justify-center bg-background">
            <div className="text-center">
              <FolderOpen className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">File Explorer View</p>
            </div>
          </div>
        )
      case "planner":
        return (
          <div className="flex-1 flex items-center justify-center bg-background">
            <div className="text-center">
              <LayoutGrid className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">Planner View</p>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      <div className="flex items-center justify-between px-6 py-3 border-b border-border">
        <div className="flex items-center gap-3">
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

        <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
          {views.map((view) => (
            <div key={view.id} className="relative group/tooltip">
              <button
                onClick={() => setActiveView(view.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  activeView === view.id
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/50"
                }`}
              >
                {view.icon}
                {activeView === view.id && <span>{view.label}</span>}
              </button>
              {/* Tooltip for inactive tabs */}
              {activeView !== view.id && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none whitespace-nowrap border border-border z-50">
                  {view.label}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-popover" />
                </div>
              )}
            </div>
          ))}
          <Button variant="ghost" size="icon" className="h-8 w-8 ml-1">
            <Plus className="w-4 h-4" />
          </Button>
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
          <Button variant="ghost" size="sm" className="h-8 text-xs">
            <ExternalLink className="w-3 h-3 mr-1" />
            Publish
          </Button>
          <Button size="sm" className="h-8 text-xs bg-[#6366f1] hover:bg-[#5558e3]">
            Share
          </Button>
        </div>
      </div>

      {renderView()}
    </div>
  )
}
