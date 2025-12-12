/**
 * TypingIndicator - ChatGPT-style animated typing indicator
 * 
 * Shows when agent is thinking/processing with animated bouncing dots
 * Appears inline in chat flow for natural UX like ChatGPT/Claude
 */

interface TypingIndicatorProps {
  agentName: string
  message?: string
  avatar?: string | null
}

export function TypingIndicator({ agentName, message, avatar }: TypingIndicatorProps) {
  return (
    <div className="flex items-start gap-3 mb-4">
      {/* Agent Avatar */}
      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0 text-lg overflow-hidden">
        {avatar ? (
          <img 
            src={avatar} 
            alt={agentName}
            className="w-8 h-8 rounded-full object-cover"
          />
        ) : (
          <span>🤖</span>
        )}
      </div>
      
      {/* Typing Animation */}
      <div className="flex-1">
        <div className="text-xs font-medium text-muted-foreground mb-1">
          {agentName}
        </div>
        <div className="bg-muted rounded-lg px-4 py-3 inline-block">
          {/* Bouncing Dots */}
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        </div>
        {message && (
          <div className="text-xs text-muted-foreground mt-1">
            {message}
          </div>
        )}
      </div>
    </div>
  )
}
