
import { Download, Zap, User, Users, Flag, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { KanbanCardData } from "./kanban-card"

interface TaskDetailModalProps {
  card: KanbanCardData | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadResult: (card: KanbanCardData) => void
}

export function TaskDetailModal({ card, open, onOpenChange, onDownloadResult }: TaskDetailModalProps) {
  if (!card) return null

  // Get type badge color
  const getTypeBadgeColor = (type?: string) => {
    switch (type) {
      case "Epic":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "User Story":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "Task":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      case "Sub-task":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Get status badge color
  const getStatusBadgeColor = (status?: string) => {
    switch (status) {
      case "Backlog":
        return "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20"
      case "Todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "Doing":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "Done":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {card.type && (
                  <Badge variant="outline" className={getTypeBadgeColor(card.type)}>
                    {card.type}
                  </Badge>
                )}
                {card.status && (
                  <Badge variant="outline" className={getStatusBadgeColor(card.status)}>
                    {card.status}
                  </Badge>
                )}
                {card.rank !== undefined && card.rank !== null && (
                  <Badge
                    variant="outline"
                    className={`gap-1 ${
                      card.rank <= 3
                        ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
                        : card.rank <= 7
                        ? "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
                        : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                    }`}
                  >
                    <Flag className="w-3 h-3" />
                    Thứ tự: {card.rank}
                  </Badge>
                )}
              </div>
              <div className="text-base font-semibold text-foreground">{card.content}</div>
              <div className="text-xs text-muted-foreground font-normal mt-1">
                ID: {card.taskId?.slice(0, 8) || 'N/A'}
              </div>
            </div>
          </DialogTitle>
        </DialogHeader>

        <Separator />

        <div className="space-y-4 text-sm">
          {/* Description */}
          {card.description && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Mô tả</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{card.description}</p>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Story Points / Estimate */}
            {(card.story_point !== undefined && card.story_point !== null) && (
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Story Points</div>
                  <div className="text-sm font-medium">{card.story_point} SP</div>
                </div>
              </div>
            )}

            {(card.estimate_value !== undefined && card.estimate_value !== null) && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Ước lượng</div>
                  <div className="text-sm font-medium">{card.estimate_value} giờ</div>
                </div>
              </div>
            )}

            {/* Assignee */}
            {card.assignee_id && (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người thực hiện</div>
                  <div className="text-sm font-medium font-mono">
                    {card.assignee_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {card.type === "Task" && card.estimate_value ? "Developer" :
                     card.type === "Sub-task" ? "Developer/Tester" : "Developer"}
                  </div>
                </div>
              </div>
            )}

            {/* Reviewer */}
            {card.reviewer_id && (
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người review</div>
                  <div className="text-sm font-medium font-mono">
                    {card.reviewer_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">Tester</div>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Agent Info (Legacy) */}
          {card.agentName && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Agent đã xử lý</h4>
              <div className="flex items-center gap-2">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={card.agentAvatar || "/placeholder.svg"} alt={card.agentName} />
                  <AvatarFallback className="bg-primary/10 text-primary text-xs">
                    {card.agentName?.charAt(0) || "A"}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{card.agentName}</span>
              </div>
            </div>
          )}

          {/* Branch */}
          {card.branch && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Branch</h4>
              <code className="text-xs bg-muted px-2 py-1 rounded">{card.branch}</code>
            </div>
          )}

          {/* Subtasks */}
          {card.subtasks && card.subtasks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Subtasks</h4>
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
                <h4 className="text-sm font-semibold text-foreground">Kết quả</h4>
                <Button size="sm" variant="outline" onClick={() => onDownloadResult(card)} className="h-7 text-xs">
                  <Download className="w-3 h-3 mr-1" />
                  Tải xuống .md
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
