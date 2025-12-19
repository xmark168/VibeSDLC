import { AlertCircle, FileCode, GitCompare, Loader2, X } from "lucide-react"
import { useEffect, useState } from "react"
import { type FileDiffResponse, getFileDiff } from "@/apis/files"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface DiffViewerProps {
  projectId: string
  filePath: string
  worktree?: string
  onClose: () => void
}

interface DiffLine {
  type: "add" | "remove" | "context" | "header" | "hunk"
  content: string
  oldLineNum?: number
  newLineNum?: number
}

function parseDiff(diff: string): DiffLine[] {
  if (!diff) return []

  const lines: DiffLine[] = []
  const rawLines = diff.split("\n")

  let oldLineNum = 0
  let newLineNum = 0

  for (const line of rawLines) {
    if (
      line.startsWith("diff --git") ||
      line.startsWith("index ") ||
      line.startsWith("---") ||
      line.startsWith("+++")
    ) {
      lines.push({ type: "header", content: line })
    } else if (line.startsWith("@@")) {
      // Parse hunk header: @@ -start,count +start,count @@
      const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/)
      if (match) {
        oldLineNum = parseInt(match[1], 10)
        newLineNum = parseInt(match[2], 10)
      }
      lines.push({ type: "hunk", content: line })
    } else if (line.startsWith("+")) {
      lines.push({
        type: "add",
        content: line.substring(1),
        newLineNum: newLineNum++,
      })
    } else if (line.startsWith("-")) {
      lines.push({
        type: "remove",
        content: line.substring(1),
        oldLineNum: oldLineNum++,
      })
    } else if (line.startsWith(" ") || line === "") {
      lines.push({
        type: "context",
        content: line.substring(1) || "",
        oldLineNum: oldLineNum++,
        newLineNum: newLineNum++,
      })
    }
  }

  return lines
}

export function DiffViewer({
  projectId,
  filePath,
  worktree,
  onClose,
}: DiffViewerProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [diffData, setDiffData] = useState<FileDiffResponse | null>(null)

  useEffect(() => {
    const fetchDiff = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getFileDiff(projectId, filePath, worktree)
        setDiffData(data)
      } catch (err: any) {
        setError(err.message || "Failed to load diff")
      } finally {
        setIsLoading(false)
      }
    }
    fetchDiff()
  }, [projectId, filePath, worktree])

  const fileName = filePath.split("/").pop() || filePath
  const diffLines = diffData?.diff ? parseDiff(diffData.diff) : []

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col bg-background">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">{fileName}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex flex-col bg-background">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">{fileName}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-destructive">
          <AlertCircle className="w-8 h-8" />
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  // No changes
  if (!diffData?.has_changes) {
    return (
      <div className="h-full flex flex-col bg-background">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">{fileName}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <FileCode className="w-8 h-8" />
          <p className="text-sm">No changes in this file</p>
        </div>
      </div>
    )
  }

  // Count additions and deletions
  const additions = diffLines.filter((l) => l.type === "add").length
  const deletions = diffLines.filter((l) => l.type === "remove").length

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">{fileName}</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-green-600 font-medium">+{additions}</span>
            <span className="text-red-500 font-medium">-{deletions}</span>
          </div>
          {diffData.base_branch && (
            <span className="text-xs text-muted-foreground">
              vs {diffData.base_branch}
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Diff content */}
      <ScrollArea className="flex-1">
        <div className="font-mono text-xs">
          {diffLines.map((line, idx) => (
            <div
              key={idx}
              className={cn(
                "flex",
                line.type === "add" && "bg-green-500/10",
                line.type === "remove" && "bg-red-500/10",
                line.type === "header" && "bg-muted/50 text-muted-foreground",
                line.type === "hunk" && "bg-blue-500/10 text-blue-600",
              )}
            >
              {/* Line numbers */}
              {line.type !== "header" && line.type !== "hunk" && (
                <>
                  <span className="w-10 px-2 text-right text-muted-foreground select-none border-r border-border/50">
                    {line.type !== "add" ? line.oldLineNum : ""}
                  </span>
                  <span className="w-10 px-2 text-right text-muted-foreground select-none border-r border-border/50">
                    {line.type !== "remove" ? line.newLineNum : ""}
                  </span>
                </>
              )}

              {/* Sign */}
              <span
                className={cn(
                  "w-5 px-1 text-center select-none",
                  line.type === "add" && "text-green-600",
                  line.type === "remove" && "text-red-500",
                )}
              >
                {line.type === "add" ? "+" : line.type === "remove" ? "-" : " "}
              </span>

              {/* Content */}
              <pre
                className={cn(
                  "flex-1 px-2 py-0.5 whitespace-pre overflow-x-auto",
                  line.type === "header" && "col-span-full",
                  line.type === "hunk" && "col-span-full",
                )}
              >
                {line.content}
              </pre>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
