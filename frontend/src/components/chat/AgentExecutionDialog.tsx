/**
 * Agent Execution Dialog
 * 
 * Shows real-time agent execution progress in a floating dialog:
 * - Progress steps
 * - Tool calls
 * - Auto-closes after completion
 */

import { Execution } from '@/hooks/useChatWebSocket'

interface AgentExecutionDialogProps {
  execution: Execution | null
}

export function AgentExecutionDialog({ execution }: AgentExecutionDialogProps) {
  if (!execution) return null
  
  return (
    <div className="fixed bottom-20 right-4 w-80 bg-card border rounded-lg shadow-lg p-4 animate-in slide-in-from-bottom-5">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🤖</span>
        <span className="font-medium text-sm">{execution.agent_name}</span>
      </div>
      
      {/* Steps */}
      {execution.steps.length > 0 && (
        <div className="space-y-1 mb-3">
          {execution.steps.map((step, i) => {
            const isLast = i === execution.steps.length - 1
            return (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 flex-shrink-0">
                  {isLast ? '→' : '✓'}
                </span>
                <span className={isLast ? 'text-foreground' : 'text-muted-foreground'}>
                  {step}
                </span>
              </div>
            )
          })}
        </div>
      )}
      
      {/* Tool Calls */}
      {execution.tools.length > 0 && (
        <div className="space-y-1 border-t pt-2 mt-2">
          {execution.tools.map(tool => (
            <div key={tool.id} className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>🔧</span>
              <span className="flex-1 truncate">{tool.action}</span>
              <span>
                {tool.state === 'completed' && '✓'}
                {tool.state === 'failed' && '✗'}
                {tool.state === 'started' && (
                  <span className="inline-block animate-spin">⏳</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      
      {/* Empty state */}
      {execution.steps.length === 0 && execution.tools.length === 0 && (
        <div className="text-xs text-muted-foreground">
          Initializing...
        </div>
      )}
    </div>
  )
}
