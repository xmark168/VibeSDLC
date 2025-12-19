import Editor from "@monaco-editor/react"
import {
  ChevronDown,
  ChevronRight,
  File,
  FilePlus,
  Folder,
  FolderOpen,
  FolderPlus,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react"
import { useEffect, useState } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  useCreateSkillFile,
  useCreateSkillFolder,
  useDeleteSkillFile,
  useDeleteSkillFolder,
  useSkillFile,
  useSkillTree,
  useUpdateSkillFile,
} from "@/queries/stacks"
import type { FileNode } from "@/types/stack"

interface SkillFileExplorerProps {
  stackCode: string
}

function getLanguageFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase()
  const langMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    json: "json",
    md: "markdown",
    yaml: "yaml",
    yml: "yaml",
    py: "python",
    html: "html",
    css: "css",
    scss: "scss",
    sql: "sql",
    sh: "shell",
    bash: "shell",
  }
  return langMap[ext || ""] || "plaintext"
}

interface TreeNodeProps {
  node: FileNode
  depth: number
  selectedPath: string | null
  expandedFolders: Set<string>
  onSelect: (path: string, type: "file" | "folder") => void
  onToggleFolder: (path: string) => void
  onCreateFile: (parentPath: string) => void
  onCreateFolder: (parentPath: string) => void
  onDelete: (path: string, type: "file" | "folder") => void
}

function TreeNode({
  node,
  depth,
  selectedPath,
  expandedFolders,
  onSelect,
  onToggleFolder,
  onCreateFile,
  onCreateFolder,
  onDelete,
}: TreeNodeProps) {
  const isFolder = node.type === "folder"
  const isExpanded = expandedFolders.has(node.path)
  const isSelected = selectedPath === node.path

  const handleClick = () => {
    if (isFolder) {
      onToggleFolder(node.path)
    }
    onSelect(node.path, node.type)
  }

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger>
          <div
            className={`flex items-center gap-1 py-1 px-2 cursor-pointer rounded hover:bg-muted ${
              isSelected ? "bg-muted" : ""
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={handleClick}
          >
            {isFolder ? (
              <>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 shrink-0 text-muted-foreground" />
                )}
                {isExpanded ? (
                  <FolderOpen className="w-4 h-4 shrink-0 text-amber-500" />
                ) : (
                  <Folder className="w-4 h-4 shrink-0 text-amber-500" />
                )}
              </>
            ) : (
              <>
                <span className="w-4" />
                <File className="w-4 h-4 shrink-0 text-muted-foreground" />
              </>
            )}
            <span className="truncate text-sm">{node.name}</span>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          {isFolder && (
            <>
              <ContextMenuItem onClick={() => onCreateFile(node.path)}>
                <FilePlus className="w-4 h-4 mr-2" />
                New File
              </ContextMenuItem>
              <ContextMenuItem onClick={() => onCreateFolder(node.path)}>
                <FolderPlus className="w-4 h-4 mr-2" />
                New Folder
              </ContextMenuItem>
              <ContextMenuSeparator />
            </>
          )}
          <ContextMenuItem
            onClick={() => onDelete(node.path, node.type)}
            className="text-destructive"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {isFolder && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              expandedFolders={expandedFolders}
              onSelect={onSelect}
              onToggleFolder={onToggleFolder}
              onCreateFile={onCreateFile}
              onCreateFolder={onCreateFolder}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function SkillFileExplorer({ stackCode }: SkillFileExplorerProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<"file" | "folder" | null>(
    null,
  )
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set([""]),
  )
  const [editorContent, setEditorContent] = useState<string>("")
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  const [createFileDialogOpen, setCreateFileDialogOpen] = useState(false)
  const [createFolderDialogOpen, setCreateFolderDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [newItemName, setNewItemName] = useState("")
  const [parentPathForCreate, setParentPathForCreate] = useState("")
  const [itemToDelete, setItemToDelete] = useState<{
    path: string
    type: "file" | "folder"
  } | null>(null)

  const {
    data: treeData,
    refetch: refetchTree,
    isLoading: isLoadingTree,
  } = useSkillTree(stackCode)
  const { data: fileData, isLoading: isLoadingFile } = useSkillFile(
    stackCode,
    selectedType === "file" && selectedPath ? selectedPath : "",
  )

  const createFile = useCreateSkillFile()
  const updateFile = useUpdateSkillFile()
  const deleteFile = useDeleteSkillFile()
  const createFolder = useCreateSkillFolder()
  const deleteFolder = useDeleteSkillFolder()

  useEffect(() => {
    if (fileData?.content !== undefined) {
      setEditorContent(fileData.content)
      setHasUnsavedChanges(false)
    }
  }, [fileData])

  const handleSelect = (path: string, type: "file" | "folder") => {
    if (hasUnsavedChanges && selectedPath !== path) {
      if (!confirm("You have unsaved changes. Discard them?")) {
        return
      }
    }
    setSelectedPath(path)
    setSelectedType(type)
    if (type === "folder") {
      setEditorContent("")
    }
    setHasUnsavedChanges(false)
  }

  const handleToggleFolder = (path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleEditorChange = (value: string | undefined) => {
    setEditorContent(value || "")
    setHasUnsavedChanges(true)
  }

  const handleSave = async () => {
    if (!selectedPath || selectedType !== "file") return
    await updateFile.mutateAsync({
      code: stackCode,
      path: selectedPath,
      content: editorContent,
    })
    setHasUnsavedChanges(false)
  }

  const handleCreateFile = (parentPath: string) => {
    setParentPathForCreate(parentPath)
    setNewItemName("")
    setCreateFileDialogOpen(true)
  }

  const handleCreateFolder = (parentPath: string) => {
    setParentPathForCreate(parentPath)
    setNewItemName("")
    setCreateFolderDialogOpen(true)
  }

  const handleDelete = (path: string, type: "file" | "folder") => {
    setItemToDelete({ path, type })
    setDeleteDialogOpen(true)
  }

  const confirmCreateFile = async () => {
    if (!newItemName.trim()) return
    const path = parentPathForCreate
      ? `${parentPathForCreate}/${newItemName}`
      : newItemName
    await createFile.mutateAsync({ code: stackCode, path, content: "" })
    setCreateFileDialogOpen(false)
    refetchTree()
  }

  const confirmCreateFolder = async () => {
    if (!newItemName.trim()) return
    const path = parentPathForCreate
      ? `${parentPathForCreate}/${newItemName}`
      : newItemName
    await createFolder.mutateAsync({ code: stackCode, path })
    setCreateFolderDialogOpen(false)
    refetchTree()
  }

  const confirmDelete = async () => {
    if (!itemToDelete) return
    if (itemToDelete.type === "file") {
      await deleteFile.mutateAsync({ code: stackCode, path: itemToDelete.path })
    } else {
      await deleteFolder.mutateAsync({
        code: stackCode,
        path: itemToDelete.path,
      })
    }
    if (selectedPath === itemToDelete.path) {
      setSelectedPath(null)
      setSelectedType(null)
      setEditorContent("")
    }
    setDeleteDialogOpen(false)
    setItemToDelete(null)
    refetchTree()
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault()
        if (hasUnsavedChanges && selectedPath && selectedType === "file") {
          handleSave()
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [hasUnsavedChanges, selectedPath, selectedType, handleSave])

  return (
    <div className="flex h-full rounded-lg overflow-hidden border">
      {/* File Explorer Sidebar */}
      <div className="w-72 border-r flex flex-col bg-muted/30">
        <div className="p-2 border-b flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Files
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleCreateFile("")}
              title="New File"
            >
              <FilePlus className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleCreateFolder("")}
              title="New Folder"
            >
              <FolderPlus className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => refetchTree()}
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-auto py-2">
          {isLoadingTree ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading...
            </div>
          ) : treeData?.children?.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              No files yet. Create your first file or folder.
            </div>
          ) : (
            treeData?.children?.map((node) => (
              <TreeNode
                key={node.path}
                node={node}
                depth={0}
                selectedPath={selectedPath}
                expandedFolders={expandedFolders}
                onSelect={handleSelect}
                onToggleFolder={handleToggleFolder}
                onCreateFile={handleCreateFile}
                onCreateFolder={handleCreateFolder}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex flex-col">
        <div className="px-4 py-2 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            {selectedPath && selectedType === "file" && (
              <>
                <File className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{selectedPath}</span>
                {hasUnsavedChanges && (
                  <span className="text-xs text-amber-500">● Modified</span>
                )}
              </>
            )}
          </div>
          {selectedPath && selectedType === "file" && (
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!hasUnsavedChanges || updateFile.isPending}
            >
              <Save className="w-4 h-4 mr-1" />
              {updateFile.isPending ? "Saving..." : "Save"}
            </Button>
          )}
        </div>

        <div className="flex-1">
          {selectedPath && selectedType === "file" ? (
            isLoadingFile ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                Loading file...
              </div>
            ) : (
              <Editor
                height="100%"
                language={getLanguageFromPath(selectedPath)}
                value={editorContent}
                onChange={handleEditorChange}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  automaticLayout: true,
                }}
              />
            )
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              {selectedType === "folder"
                ? "Select a file to edit"
                : "Select a file from the tree to edit"}
            </div>
          )}
        </div>
      </div>

      {/* Create File Dialog */}
      <Dialog
        open={createFileDialogOpen}
        onOpenChange={setCreateFileDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New File</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="filename.md"
              onKeyDown={(e) => e.key === "Enter" && confirmCreateFile()}
              autoFocus
            />
            {parentPathForCreate && (
              <p className="text-xs text-muted-foreground mt-2">
                Location: {parentPathForCreate}/
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateFileDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmCreateFile}
              disabled={!newItemName.trim() || createFile.isPending}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Folder Dialog */}
      <Dialog
        open={createFolderDialogOpen}
        onOpenChange={setCreateFolderDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Folder</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="folder-name"
              onKeyDown={(e) => e.key === "Enter" && confirmCreateFolder()}
              autoFocus
            />
            {parentPathForCreate && (
              <p className="text-xs text-muted-foreground mt-2">
                Location: {parentPathForCreate}/
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateFolderDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmCreateFolder}
              disabled={!newItemName.trim() || createFolder.isPending}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {itemToDelete?.type === "folder" ? "Folder" : "File"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{itemToDelete?.path}"?
              {itemToDelete?.type === "folder" &&
                " This will delete all contents inside."}
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
