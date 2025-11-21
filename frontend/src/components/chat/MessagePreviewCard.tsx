import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ProductBriefPreview, BacklogPreview } from './previews'

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

  // Don't render if not a structured message type
  if (!message.message_type || message.message_type === 'text') {
    return null
  }

  const renderPreview = () => {
    if (!isExpanded || !message.structured_data) return null

    // Get actual data - backend sends { phase, message_type, data: {...} }
    const data = message.structured_data.data || message.structured_data

    switch (message.message_type) {
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
        return (
          <div className="space-y-4 max-h-[400px] overflow-y-auto">
            {flowsData.map((flow: any, index: number) => (
              <div key={index} className="border rounded-lg p-4">
                <h4 className="font-semibold text-sm">{flow.name}</h4>
                <p className="text-xs text-muted-foreground mt-1">{flow.description}</p>
                {flow.steps && (
                  <div className="mt-2">
                    <p className="text-xs font-medium">Các bước:</p>
                    <ol className="list-decimal list-inside text-xs mt-1 space-y-1">
                      {flow.steps.map((step: string, i: number) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
                {flow.actors && (
                  <p className="text-xs mt-2"><strong>Actors:</strong> {flow.actors.join(', ')}</p>
                )}
              </div>
            ))}
          </div>
        )
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
    switch (message.message_type) {
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
