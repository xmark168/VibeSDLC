import { useState } from 'react'
import { ChevronDown, ChevronRight, Edit } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ProductBriefPreview, ProductVisionPreview, BacklogPreview } from './previews'

interface MessagePreviewCardProps {
  message: {
    id: string
    message_type: string
    content: string
    structured_data: any
    metadata?: any
    created_at: string
  }
  onEdit?: (message: any) => void
}

export function MessagePreviewCard({ message, onEdit }: MessagePreviewCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Don't render if not a structured message type
  if (!message.message_type || message.message_type === 'text') {
    return null
  }

  const renderPreview = () => {
    if (!isExpanded || !message.structured_data) return null

    switch (message.message_type) {
      case 'product_brief':
        return (
          <ProductBriefPreview
            brief={message.structured_data}
            incompleteFlag={message.metadata?.incomplete_flag}
          />
        )
      case 'product_vision':
        return (
          <ProductVisionPreview
            vision={message.structured_data}
            qualityScore={message.metadata?.quality_score}
            validationResult={message.metadata?.validation_result}
          />
        )
      case 'product_backlog':
        return (
          <BacklogPreview
            backlog={message.structured_data}
          />
        )
      case 'sprint_plan':
        return <div className="text-sm text-muted-foreground">Sprint planning is no longer supported in Kanban mode</div>
      default:
        return <div className="text-sm text-muted-foreground">Unknown preview type</div>
    }
  }

  const getTypeLabel = () => {
    switch (message.message_type) {
      case 'product_brief':
        return '📋 Product Brief'
      case 'product_vision':
        return '🎯 Product Vision'
      case 'product_backlog':
        return '📊 Product Backlog'
      case 'sprint_plan':
        return '🏃 Sprint Plan'
      default:
        return 'Preview'
    }
  }

  return (
    <Card className="my-3 border-blue-200 dark:border-blue-800">
      <CardHeader
        className="cursor-pointer hover:bg-accent/50 transition-colors py-3"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
            <div>
              <div className="text-sm font-semibold">{getTypeLabel()}</div>
              {/* <div className="text-xs text-muted-foreground">{message.content}</div> */}
            </div>
          </div>
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onEdit(message)
              }}
              className="flex items-center gap-1"
            >
              <Edit className="w-3 h-3" />
              Edit
            </Button>
          )}
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0">
          {renderPreview()}
        </CardContent>
      )}
    </Card>
  )
}
