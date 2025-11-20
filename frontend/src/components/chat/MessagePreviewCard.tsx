import { useState } from 'react'
import { ChevronDown, ChevronRight, Edit } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
          <div className="space-y-4">
            {flowsData.map((flow: any, index: number) => (
              <div key={index} className="border rounded-lg p-4">
                <h4 className="font-semibold text-sm">{flow.name}</h4>
                <p className="text-xs text-muted-foreground mt-1">{flow.description}</p>
                {flow.steps && (
                  <div className="mt-2">
                    <p className="text-xs font-medium">Steps:</p>
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
