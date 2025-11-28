import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { FileText, ExternalLink, Check, Pencil, X } from "lucide-react"

interface PrdCreatedCardProps {
  title: string
  filePath: string
  status?: 'pending' | 'approved' | 'editing'
  onView?: () => void
  onApprove?: () => void
  onEdit?: (feedback: string) => void
}

export function PrdCreatedCard({ 
  title, 
  filePath, 
  status = 'pending',
  onView, 
  onApprove,
  onEdit 
}: PrdCreatedCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [feedback, setFeedback] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleApprove = () => {
    setIsLoading(true)
    onApprove?.()
    // Loading will stay until new message arrives
  }

  const handleSubmitEdit = () => {
    if (!feedback.trim()) return
    setIsLoading(true)
    onEdit?.(feedback)
    // Keep loading, hide editing form
    setIsEditing(false)
    setFeedback("")
  }

  // Already approved
  if (status === 'approved') {
    return (
      <Card className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/20">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-500/20">
            <Check className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-green-700 dark:text-green-400">
              ✅ PRD đã được phê duyệt
            </h4>
            <p className="text-xs text-muted-foreground">{title}</p>
          </div>
          <Button size="sm" variant="outline" onClick={onView}>
            <ExternalLink className="w-3.5 h-3.5 mr-1" />
            View
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-4 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border-blue-500/20">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <FileText className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-blue-700 dark:text-blue-400">
              📋 PRD đã được tạo - Chờ phê duyệt
            </h4>
            <p className="text-xs text-muted-foreground">{title}</p>
          </div>
          <Button size="sm" variant="outline" onClick={onView}>
            <ExternalLink className="w-3.5 h-3.5 mr-1" />
            View
          </Button>
        </div>

        {/* Submitted state - show after user submits approve/edit */}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <Check className="w-4 h-4" />
            <span>Đã gửi yêu cầu</span>
          </div>
        )}

        {/* Edit feedback input */}
        {isEditing && !isLoading && (
          <div className="space-y-2">
            <Textarea
              placeholder="Nhập yêu cầu chỉnh sửa PRD..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="min-h-[80px] text-sm"
            />
            <div className="flex gap-2">
              <Button 
                size="sm" 
                onClick={handleSubmitEdit}
                disabled={!feedback.trim()}
              >
                <Check className="w-3.5 h-3.5 mr-1" />
                Gửi yêu cầu
              </Button>
              <Button 
                size="sm" 
                variant="ghost"
                onClick={() => {
                  setIsEditing(false)
                  setFeedback("")
                }}
              >
                <X className="w-3.5 h-3.5 mr-1" />
                Hủy
              </Button>
            </div>
          </div>
        )}

        {/* Action buttons */}
        {!isEditing && !isLoading && (
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="bg-green-600 hover:bg-green-700"
              onClick={handleApprove}
            >
              <Check className="w-3.5 h-3.5 mr-1" />
              Phê duyệt
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => setIsEditing(true)}
            >
              <Pencil className="w-3.5 h-3.5 mr-1" />
              Yêu cầu chỉnh sửa
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}
