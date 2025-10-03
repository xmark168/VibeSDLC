
import { useState } from "react"
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface FileNode {
  name: string
  type: "file" | "folder"
  path: string
  children?: FileNode[]
  modified?: string
}

const fileTree: FileNode[] = [
  {
    name: "app",
    type: "folder",
    path: "app",
    children: [
      {
        name: "styles",
        type: "folder",
        path: "app/styles",
        children: [
          { name: "globals.css", type: "file", path: "app/styles/globals.css" },
          { name: "theme.css", type: "file", path: "app/styles/theme.css" },
        ],
      },
      { name: "layout.tsx", type: "file", path: "app/layout.tsx" },
      { name: "page.tsx", type: "file", path: "app/page.tsx" },
    ],
  },
  {
    name: "components",
    type: "folder",
    path: "components",
    children: [
      {
        name: "kanban",
        type: "folder",
        path: "components/kanban",
        children: [
          { name: "kanban-board.tsx", type: "file", path: "components/kanban/kanban-board.tsx" },
          { name: "kanban-card.tsx", type: "file", path: "components/kanban/kanban-card.tsx" },
          { name: "kanban-column.tsx", type: "file", path: "components/kanban/kanban-column.tsx" },
        ],
      },
      { name: "chat-panel.tsx", type: "file", path: "components/chat-panel.tsx" },
      { name: "resizable-handle.tsx", type: "file", path: "components/resizable-handle.tsx", modified: "+2/-2" },
      { name: "sidebar.tsx", type: "file", path: "components/sidebar.tsx" },
      { name: "task-detail-modal.tsx", type: "file", path: "components/task-detail-modal.tsx" },
      { name: "theme-toggle.tsx", type: "file", path: "components/theme-toggle.tsx" },
      { name: "workspace-panel.tsx", type: "file", path: "components/workspace-panel.tsx" },
    ],
  },
  {
    name: "public",
    type: "folder",
    path: "public",
    children: [
      {
        name: "images",
        type: "folder",
        path: "public/images",
        children: [
          {
            name: "abstract-infinity-symbol.jpg",
            type: "file",
            path: "public/images/abstract-infinity-symbol.jpg",
          },
        ],
      },
    ],
  },
  { name: "package.json", type: "file", path: "package.json" },
];


interface FileExplorerProps {
  onFileSelect: (path: string) => void
  selectedFile: string | null
}

export function FileExplorer({ onFileSelect, selectedFile }: FileExplorerProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(["components"]))

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedFolders(newExpanded)
  }

  const renderNode = (node: FileNode, depth = 0) => {
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = selectedFile === node.path

    if (node.type === "folder") {
      return (
        <div key={node.path}>
          <button
            onClick={() => toggleFolder(node.path)}
            className="w-full flex items-center gap-1.5 px-2 py-1 text-sm hover:bg-accent/50 transition-colors"
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            )}
            <span className="text-foreground truncate">{node.name}</span>
          </button>
          {isExpanded && node.children && <div>{node.children.map((child) => renderNode(child, depth + 1))}</div>}
        </div>
      )
    }

    return (
      <button
        key={node.path}
        onClick={() => onFileSelect(node.path)}
        className={cn(
          "w-full flex items-center gap-1.5 px-2 py-1 text-sm hover:bg-accent/50 transition-colors group",
          isSelected && "bg-accent",
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <div className="w-3.5 flex-shrink-0" />
        <File className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="text-foreground truncate flex-1 text-left">{node.name}</span>
        {node.modified && (
          <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
            {node.modified}
          </span>
        )}
      </button>
    )
  }

  return (
    <div className="h-full overflow-y-auto bg-background border-r border-border">
      <div className="py-2">{fileTree.map((node) => renderNode(node))}</div>
    </div>
  )
}
