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
import { filesApi, type FileNode, type GitStatusResponse, type BranchesResponse, type Worktree } from "@/apis/files"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface FileExplorerProps {
  projectId?: string
  onFileSelect: (path: string, worktree?: string) => void
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
  
  // Branch/worktree state
  const [branches, setBranches] = useState<BranchesResponse | null>(null)
  const [selectedWorktree, setSelectedWorktree] = useState<string | null>(null)

  // Fetch file tree when projectId or selectedWorktree changes
  useEffect(() => {
    if (projectId) {
      fetchFileTree()
      fetchGitStatus()
      fetchBranches()
    } else {
      setFileTree([])
      setError(null)
      setGitStatus(null)
      setBranches(null)
      setSelectedWorktree(null)
    }
  }, [projectId, selectedWorktree])

  // Listen for WebSocket branch_changed events
  useEffect(() => {
    if (!projectId) return
    
    const handleBranchChanged = (event: CustomEvent) => {
      if (event.detail.project_id === projectId) {
        setBranches(prev => prev ? { ...prev, current: event.detail.branch } : null)
        fetchFileTree()
        fetchGitStatus()
      }
    }
    
    window.addEventListener('branch-changed', handleBranchChanged as EventListener)
    return () => window.removeEventListener('branch-changed', handleBranchChanged as EventListener)
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
      const response = await filesApi.getFileTree(projectId, 5, selectedWorktree || undefined)

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

  const fetchBranches = async () => {
    if (!projectId) return

    try {
      const response = await filesApi.getBranches(projectId)
      setBranches(response)
    } catch (err: any) {
      console.error("Failed to fetch branches:", err)
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
        onClick={() => onFileSelect(node.path, selectedWorktree || undefined)}
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

  // Get current worktree info
  const currentWorktree = selectedWorktree 
    ? branches?.worktrees.find(w => w.path === selectedWorktree)
    : branches?.worktrees.find(w => w.branch === branches.current)
  
  const currentBranch = currentWorktree?.branch || branches?.current

  return (
    <div className="h-full flex flex-col bg-background border-r border-border">
      {/* Worktree/Branch selector */}
      {branches && branches.worktrees.length > 0 && (
        <div className="px-2 py-2 border-b border-border">
          <Select 
            value={selectedWorktree || branches.worktrees[0]?.path || ""} 
            onValueChange={(path) => setSelectedWorktree(path)}
          >
            <SelectTrigger className="h-8 text-xs">
              <div className="flex items-center gap-2">
                <GitBranch className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate">{currentBranch || "Select branch"}</span>
              </div>
            </SelectTrigger>
            <SelectContent>
              {branches.worktrees.map((wt) => (
                <SelectItem key={wt.path} value={wt.path} className="text-xs">
                  <span className="truncate">{wt.branch || wt.path}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      
      {/* Simple branch indicator when no worktrees */}
      {branches && branches.current && branches.worktrees.length === 0 && (
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <GitBranch className="w-3.5 h-3.5" />
            <span className="font-medium text-foreground truncate">
              {branches.current}
            </span>
          </div>
        </div>
      )}
      
      {/* File tree */}
      <div className="flex-1 overflow-y-auto py-2">
        {fileTree.map((node) => renderNode(node))}
      </div>
    </div>
  )
}

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
