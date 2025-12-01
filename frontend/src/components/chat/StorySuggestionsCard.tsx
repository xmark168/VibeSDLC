import { useState } from "react"
import { 
  Search, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Sparkles,
  ChevronDown,
  Check
} from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { storiesApi } from "@/apis/stories"
import { toast } from "sonner"

interface InvestIssue {
  code: string
  issue: string
}

interface StorySuggestionsCardProps {
  storyId: string
  storyTitle: string
  isDuplicate?: boolean
  duplicateOf?: string
  investScore: number
  investIssues?: InvestIssue[]
  suggestedTitle?: string
  suggestedAcceptanceCriteria?: string[]
  suggestedRequirements?: string[]
  hasSuggestions?: boolean
  initialActionTaken?: 'applied' | 'kept' | 'removed' | null
  onApplied?: () => void
  onKeep?: () => void
  onRemove?: () => void
}

export function StorySuggestionsCard({
  storyId,
  storyTitle,
  isDuplicate = false,
  duplicateOf,
  investScore,
  investIssues = [],
  suggestedTitle,
  suggestedAcceptanceCriteria,
  suggestedRequirements,
  hasSuggestions = false,
  initialActionTaken = null,
  onApplied,
  onKeep,
  onRemove
}: StorySuggestionsCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [isRemoving, setIsRemoving] = useState(false)
  const [actionTaken, setActionTaken] = useState<'applied' | 'kept' | 'removed' | null>(initialActionTaken)

  const getScoreStyle = () => {
    return "from-blue-500/10 to-blue-500/10 border-blue-500/20"
  }

  const getScoreIconBg = () => {
    return "bg-blue-500/20"
  }

  const getScoreIconColor = () => {
    return "text-blue-600"
  }

  const handleApplySuggestions = async () => {
    if (!hasSuggestions) return
    
    setIsApplying(true)
    try {
      await storiesApi.reviewAction(storyId, 'apply', {
        suggested_title: suggestedTitle,
        suggested_acceptance_criteria: suggestedAcceptanceCriteria,
        suggested_requirements: suggestedRequirements
      })
      setActionTaken('applied')
      onApplied?.()
    } catch (error) {
      console.error("Failed to apply suggestions:", error)
      toast.error("Không thể áp dụng gợi ý")
    } finally {
      setIsApplying(false)
    }
  }

  const handleKeep = async () => {
    try {
      await storiesApi.reviewAction(storyId, 'keep')
      setActionTaken('kept')
      onKeep?.()
    } catch (error) {
      console.error("Failed to keep story:", error)
      toast.error("Có lỗi xảy ra")
    }
  }

  const handleRemove = async () => {
    setIsRemoving(true)
    try {
      await storiesApi.reviewAction(storyId, 'remove')
      setActionTaken('removed')
      onRemove?.()
    } catch (error) {
      console.error("Failed to remove story:", error)
      toast.error("Không thể loại bỏ story")
    } finally {
      setIsRemoving(false)
    }
  }

  return (
    <Card className={`p-4 bg-gradient-to-r ${getScoreStyle()}`}>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${getScoreIconBg()}`}>
            <Search className={`w-5 h-5 ${getScoreIconColor()}`} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-foreground">
              🔍 Review Story
            </h4>
          </div>
          {/* Only show INVEST score if not duplicate */}
          {!isDuplicate && (
            <Badge 
              variant="outline" 
              className="rounded-full px-3 py-1 border-border font-normal bg-background"
            >
              INVEST: {investScore}/6
            </Badge>
          )}
          {/* Expand button - only show if NOT duplicate */}
          {!isDuplicate && (
            <Button 
              size="icon"
              variant="outline" 
              className="rounded-full h-8 w-8"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
            </Button>
          )}
        </div>

        {/* Duplicate Warning - Always show if duplicate */}
        {isDuplicate && duplicateOf && (
          <div className="flex items-center gap-2 text-sm text-yellow-600 dark:text-yellow-400">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>Bị trùng với story <strong>"{duplicateOf}"</strong></span>
          </div>
        )}

        {/* Action taken state */}
        {actionTaken && (
          <div className="flex items-center gap-2 text-sm ">
            <Check className="w-4 h-4" />
            <span>
              {actionTaken === 'applied' && 'Đã áp dụng gợi ý'}
              {actionTaken === 'kept' && 'Đã giữ nguyên story'}
              {actionTaken === 'removed' && 'Đã xóa story'}
            </span>
          </div>
        )}

        {/* Action buttons - always show if no action taken */}
        {!actionTaken && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Only show Apply button if NOT duplicate AND has suggestions */}
            {!isDuplicate && hasSuggestions && (
              <Button
                size="sm"
                className="bg-purple-600 hover:bg-purple-700 text-white"
                onClick={handleApplySuggestions}
                disabled={isApplying || isRemoving}
              >
                {isApplying ? 'Đang áp dụng...' : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1" />
                    Áp dụng gợi ý
                  </>
                )}
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={handleKeep}
              disabled={isApplying || isRemoving}
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              Giữ nguyên
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={handleRemove}
              disabled={isApplying || isRemoving}
            >
              {isRemoving ? 'Đang xóa...' : (
                <>
                  <XCircle className="w-3.5 h-3.5 mr-1" />
                  Loại bỏ
                </>
              )}
            </Button>
          </div>
        )}

        {/* Expanded content */}
        {isExpanded && (
          <div className="space-y-3 pt-2 border-t border-border/50">
            {/* 1. User Story Content */}
            <div className="space-y-1">
              <p className="text-sm font-bold">Story:</p>
              <p className="text-sm pl-4">{storyTitle}</p>
            </div>

            {/* 2. Issues - Always show */}
            <div className="space-y-2">
              <p className="text-sm font-bold">Vấn đề:</p>
              {investIssues.length > 0 ? (
                investIssues.map((issue, idx) => {
                  const codeNames: Record<string, string> = {
                    'I': 'Independent',
                    'N': 'Negotiable', 
                    'V': 'Valuable',
                    'E': 'Estimable',
                    'S': 'Small',
                    'T': 'Testable'
                  }
                  return (
                    <div key={idx} className="space-y-1">
                      <p className="text-sm font-medium pl-4">
                        {issue.code} – {codeNames[issue.code] || issue.code}:
                      </p>
                      <p className="text-sm pl-8">
                        - {issue.issue}
                      </p>
                    </div>
                  )
                })
              ) : (
                <p className="text-sm pl-4">✓ Story đạt chuẩn INVEST</p>
              )}
            </div>

            {/* 3. Suggestions - Only if available */}
            {hasSuggestions && (suggestedTitle || (suggestedAcceptanceCriteria && suggestedAcceptanceCriteria.length > 0) || (suggestedRequirements && suggestedRequirements.length > 0)) && (
              <div className="space-y-2">
                <p className="text-sm font-bold">Gợi ý cải thiện:</p>

                {suggestedTitle && (
                  <div className="space-y-1">
                    <p className="text-sm font-medium pl-4">Title đề xuất:</p>
                    <p className="text-sm pl-8">- {suggestedTitle}</p>
                  </div>
                )}

                {suggestedRequirements && suggestedRequirements.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium pl-4">Requirements đề xuất:</p>
                    {suggestedRequirements.map((req, idx) => (
                      <p key={idx} className="text-sm pl-8">
                        {idx + 1}. {req}
                      </p>
                    ))}
                  </div>
                )}

                {suggestedAcceptanceCriteria && suggestedAcceptanceCriteria.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium pl-4">Acceptance Criteria đề xuất:</p>
                    {suggestedAcceptanceCriteria.map((ac, idx) => (
                      <div key={idx} className="text-sm pl-8 space-y-0.5">
                        <p>{idx + 1}. {ac.split('\n')[0]}</p>
                        {ac.split('\n').slice(1).map((line, lineIdx) => (
                          <p key={lineIdx} className="pl-4">{line}</p>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
