import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { FileText, ListTodo, ExternalLink, Check, Pencil, X, type LucideIcon } from "lucide-react"

type CardType = 'prd' | 'stories'

interface ApprovalCardProps {
  type: CardType
  title?: string
  status?: 'pending' | 'approved' | 'editing' | 'submitted'
  showActions?: boolean
  submitted?: boolean
  onView?: () => void
  onApprove?: () => void
  onEdit?: (feedback: string) => void
}

const cardConfig: Record<CardType, {
  icon: LucideIcon
  label: string
  approvedLabel: string
  placeholder: string
  colors: {
    gradient: string
    border: string
    iconBg: string
    iconColor: string
    textColor: string
  }
}> = {
  prd: {
    icon: FileText,
    label: 'PRD created',
    approvedLabel: 'PRD has been approved',
    placeholder: 'Enter PRD edit request...',
    colors: {
      gradient: 'from-blue-500/10 to-cyan-500/10',
      border: 'border-blue-500/20',
      iconBg: 'bg-blue-500/20',
      iconColor: 'text-blue-600',
      textColor: 'text-blue-700 dark:text-blue-400',
    }
  },
  stories: {
    icon: ListTodo,
    label: 'Stories created',
    approvedLabel: 'Stories have been approved',
    placeholder: 'Enter Epics/Stories edit request...',
    colors: {
      gradient: 'from-purple-500/10 to-violet-500/10',
      border: 'border-purple-500/20',
      iconBg: 'bg-purple-500/20',
      iconColor: 'text-purple-600',
      textColor: 'text-purple-700 dark:text-purple-400',
    }
  }
}

export function ApprovalCard({ 
  type,
  title, 
  status = 'pending',
  showActions = true,
  submitted = false,
  onView, 
  onApprove,
  onEdit 
}: ApprovalCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [feedback, setFeedback] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  
  const config = cardConfig[type]
  const Icon = config.icon
  const hasSubmitted = submitted || status === 'submitted' || isLoading

  const handleApprove = () => {
    setIsLoading(true)
    onApprove?.()
  }

  const handleSubmitEdit = () => {
    if (!feedback.trim()) return
    setIsLoading(true)
    onEdit?.(feedback)
    setIsEditing(false)
    setFeedback("")
  }

  if (status === 'approved') {
    return (
      <Card className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/20">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-500/20">
            <Check className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-green-700 dark:text-green-400">
               {config.approvedLabel}
            </h4>
            {title && <p className="text-xs text-muted-foreground">{title}</p>}
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
    <Card className={`p-4 bg-gradient-to-r ${config.colors.gradient} ${config.colors.border}`}>
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.colors.iconBg}`}>
            <Icon className={`w-5 h-5 ${config.colors.iconColor}`} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className={`text-sm font-medium ${config.colors.textColor}`}>
              {config.label} {!hasSubmitted && '- Awaiting approval'}
            </h4>
            {title && <p className="text-xs text-muted-foreground">{title}</p>}
          </div>
          <Button 
            size="sm" 
            variant="outline"
            className={type === 'stories' ? 'gap-1.5 border-purple-500/30 hover:bg-purple-500/10' : ''}
            onClick={onView}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View
          </Button>
        </div>

        {!showActions && (
          <div className="text-xs text-muted-foreground italic">
            Old version
          </div>
        )}

        {showActions && hasSubmitted && (
          <div className="flex items-center gap-2 text-sm">
            <Check className="w-4 h-4" />
            <span>Request submitted</span>
          </div>
        )}

        {showActions && isEditing && !hasSubmitted && (
          <div className="space-y-2">
            <Textarea
              placeholder={config.placeholder}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="min-h-[80px] text-sm bg-white dark:bg-gray-900"
            />
            <div className="flex gap-2">
              <Button 
                size="sm" 
                onClick={handleSubmitEdit}
                disabled={!feedback.trim()}
              >
                <Check className="w-3.5 h-3.5 mr-1" />
                Submit
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
                Cancel
              </Button>
            </div>
          </div>
        )}

        {showActions && !isEditing && !hasSubmitted && (
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="bg-green-600 hover:bg-green-700"
              onClick={handleApprove}
            >
              <Check className="w-3.5 h-3.5 mr-1" />
              Approve
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => setIsEditing(true)}
            >
              <Pencil className="w-3.5 h-3.5 mr-1" />
              Request edit
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}
