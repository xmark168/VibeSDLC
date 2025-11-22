import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  Loader2,
  AlertCircle,
  RefreshCw,
  GitBranch,
  Circle,
} from "lucide-react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { filesApi, type FileNode, type GitStatusResponse } from "@/apis/files"
import { Button } from "@/components/ui/button"

interface FileExplorerProps {
  projectId?: string
  onFileSelect: (path: string) => void
  selectedFile: string | null
}

export function FileExplorer({
  projectId,
  onFileSelect,
  selectedFile,
}: FileExplorerProps) {
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Git status state
  const [gitStatus, setGitStatus] = useState<GitStatusResponse | null>(null)

  // Fetch file tree when projectId changes
  useEffect(() => {
    if (projectId) {
      fetchFileTree()
      fetchGitStatus()
    } else {
      setFileTree([])
      setError(null)
      setGitStatus(null)
    }
  }, [projectId])

  // Poll git status every 5 seconds when tab is visible
  useEffect(() => {
    if (!projectId) return

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchGitStatus()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [projectId])

  const fetchFileTree = async () => {
    if (!projectId) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await filesApi.getFileTree(projectId, 5)

      // Convert root node children to array (or use root if it has children)
      if (response.root.children) {
        setFileTree(response.root.children)
        // Auto-expand first folder
        if (response.root.children.length > 0 && response.root.children[0].type === "folder") {
          setExpandedFolders(new Set([response.root.children[0].path]))
        }
      } else {
        setFileTree([])
      }
    } catch (err: any) {
      console.error("Failed to fetch file tree:", err)
      setError(err.message || "Failed to load files")
    } finally {
      setIsLoading(false)
    }
  }

  const fetchGitStatus = async () => {
    if (!projectId) return

    try {
      const response = await filesApi.getGitStatus(projectId)
      setGitStatus(response)
    } catch (err: any) {
      console.error("Failed to fetch git status:", err)
      // Silent fail - git status is optional
    }
  }

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedFolders(newExpanded)
  }

  // Get git status for a file
  const getFileChangeType = (filePath: string): string | null => {
    if (!gitStatus?.is_git_repo || !gitStatus.files) return null
    return gitStatus.files[filePath] || null
  }

  // Get color/icon for change type
  const getChangeIndicator = (changeType: string | null) => {
    if (!changeType) return null

    const indicators: Record<string, { color: string; label: string }> = {
      'M': { color: 'text-yellow-500', label: 'Modified' },
      'A': { color: 'text-green-500', label: 'Added' },
      'D': { color: 'text-red-500', label: 'Deleted' },
      'R': { color: 'text-blue-500', label: 'Renamed' },
      'U': { color: 'text-gray-500', label: 'Untracked' },
    }

    const indicator = indicators[changeType] || { color: 'text-gray-400', label: changeType }
    return (
      <Circle
        className={cn('w-2 h-2 fill-current', indicator.color)}
        title={indicator.label}
      />
    )
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
          {isExpanded && node.children && (
            <div>
              {node.children.map((child) => renderNode(child, depth + 1))}
            </div>
          )}
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
        <div className="w-3.5 flex-shrink-0 flex items-center justify-center">
          {getChangeIndicator(getFileChangeType(node.path))}
        </div>
        <File className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="text-foreground truncate flex-1 text-left">
          {node.name}
        </span>
        {node.size && (
          <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
            {formatFileSize(node.size)}
          </span>
        )}
      </button>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-r border-border">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-sm">Loading files...</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-r border-border p-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle className="w-8 h-8 text-destructive" />
          <div>
            <p className="text-sm font-medium text-foreground">Failed to load files</p>
            <p className="text-xs text-muted-foreground mt-1">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchFileTree}
            className="gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  // No project selected
  if (!projectId) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-r border-border p-4">
        <p className="text-sm text-muted-foreground text-center">
          Select a project to view files
        </p>
      </div>
    )
  }

  // Empty state
  if (fileTree.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-r border-border p-4">
        <div className="flex flex-col items-center gap-2 text-center">
          <Folder className="w-8 h-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No files in this project yet
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto bg-background border-r border-border">
      <div className="py-2">{fileTree.map((node) => renderNode(node))}</div>
    </div>
  )
}

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
