import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ProductBriefPreview, BacklogPreview, BusinessFlowsPreview } from './previews'

interface MessagePreviewCardProps {
  message: {
    id: string
    message_type?: string
    content: string
    structured_data?: any
    message_metadata?: any
    created_at: string
  }
}

export function MessagePreviewCard({ message }: MessagePreviewCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get message type - can be from message.message_type or structured_data.message_type
  const messageType = message.message_type || message.structured_data?.message_type

  // Don't render if not a structured message type
  if (!messageType || messageType === 'text') {
    return null
  }

  const renderPreview = () => {
    if (!isExpanded || !message.structured_data) return null

    // Get actual data - handle both formats:
    // 1. New format: structured_data is already the array/object
    // 2. Old format: structured_data = { message_type, data: {...} }
    const data = message.structured_data.data || message.structured_data

    switch (messageType) {
      case 'prd':
        return (
          <ProductBriefPreview
            brief={data}
            incompleteFlag={message.message_metadata?.incomplete_flag}
          />
        )
      case 'business_flows':
        // business_flows data is an array
        const flowsData = Array.isArray(data) ? data : []
        return <BusinessFlowsPreview flows={flowsData} />
      case 'product_backlog':
        return (
          <BacklogPreview
            backlog={data}
          />
        )
      default:
        return <div className="text-sm text-muted-foreground">Unknown preview type</div>
    }
  }

  const getTypeLabel = () => {
    switch (messageType) {
      case 'prd':
        return '📋 PRD'
      case 'business_flows':
        return '🔄 Business Flows'
      case 'product_backlog':
        return '📊 Product Backlog'
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
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <div className="text-sm font-semibold">{getTypeLabel()}</div>
          <span className="text-xs text-muted-foreground">
            {isExpanded ? '(click để thu gọn)' : '(click để xem)'}
          </span>
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
