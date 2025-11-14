import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import { User, Bot } from 'lucide-react'
import type { Message } from '../../types/chat'
import { AGENT_INFO } from '../../types/chat'

interface ChatMessageProps {
  message: Message
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.role === 'user'
  const agentInfo = message.agentType ? AGENT_INFO[message.agentType] : null

  return (
    <div className={cn('flex gap-3 px-4 py-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-blue-500' : 'bg-gradient-to-br',
          !isUser && agentInfo && `from-${agentInfo.color} to-${agentInfo.color}/80`
        )}
        style={
          !isUser && agentInfo
            ? {
                background: `linear-gradient(to bottom right, ${agentInfo.color}, ${agentInfo.color}dd)`,
              }
            : undefined
        }
      >
        {isUser ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
      </div>

      {/* Message Content */}
      <div className={cn('flex flex-col max-w-[70%]', isUser ? 'items-end' : 'items-start')}>
        {/* Agent Name & Timestamp */}
        <div className="flex items-center gap-2 mb-1">
          {!isUser && agentInfo && <span className="text-xs font-semibold text-gray-700">{agentInfo.name}</span>}
          <span className="text-xs text-gray-500">{format(message.timestamp, 'HH:mm', { locale: vi })}</span>
        </div>

        {/* Message Bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 shadow-sm',
            isUser
              ? 'bg-blue-500 text-white rounded-tr-sm'
              : 'bg-white border-2 border-gray-100 text-gray-900 rounded-tl-sm'
          )}
        >
          <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
        </div>
      </div>
    </div>
  )
}
