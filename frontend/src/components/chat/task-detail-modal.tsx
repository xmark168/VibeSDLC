
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import type { KanbanCardData } from "./kanban-card"

interface TaskDetailModalProps {
  card: KanbanCardData | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadResult: (card: KanbanCardData) => void
}

export function TaskDetailModal({ card, open, onOpenChange, onDownloadResult }: TaskDetailModalProps) {
  if (!card) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <Avatar className="w-10 h-10">
              <AvatarImage src={card.agentAvatar || "/placeholder.svg"} alt={card.agentName} />
              <AvatarFallback className="bg-primary/10 text-primary">{card.agentName?.charAt(0) || "A"}</AvatarFallback>
            </Avatar>
            <div>
              <div className="text-base font-semibold">{card.content}</div>
              <div className="text-xs text-muted-foreground font-normal">Task ID: {card.taskId}</div>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-4 text-sm text-muted-foreground">
          {/* Agent Info */}
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Assigned Agent</h4>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-1 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400">
                {card.agentName}
              </span>
            </div>
          </div>

          {/* Branch */}
          {card.branch && (
            <div>
              <h4 className="text-sm font-medium text-foreground mb-2">Branch</h4>
              <code className="text-xs bg-muted px-2 py-1 rounded">{card.branch}</code>
            </div>
          )}

          {/* Subtasks */}
          {card.subtasks && card.subtasks.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-foreground mb-2">Subtasks</h4>
              <ul className="space-y-1">
                {card.subtasks.map((subtask, index) => (
                  <li key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                    {subtask}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Result */}
          {card.result && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-foreground">Result</h4>
                <Button size="sm" variant="outline" onClick={() => onDownloadResult(card)} className="h-7 text-xs">
                  <Download className="w-3 h-3 mr-1" />
                  Download .md
                </Button>
              </div>
              <div className="text-sm text-muted-foreground bg-muted p-3 rounded max-h-48 overflow-y-auto">
                <pre className="whitespace-pre-wrap font-mono text-xs">{card.result}</pre>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
