import { useEffect, useRef } from 'react'
import { ChatMessage } from './ChatMessage'
import { ChatTypingIndicator } from './ChatTypingIndicator'
import type { Message } from '../../types/chat'

interface ChatMessageListProps {
  messages: Message[]
  isTyping?: boolean
}

export const ChatMessageList = ({ messages, isTyping = false }: ChatMessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-3 px-4">
            <div className="w-16 h-16 mx-auto bg-gray-200 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-700">Start a conversation</h3>
              <p className="text-sm text-gray-500 mt-1">
                Ask the AI agent about project status, create stories, or get help with workflow
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="py-4 space-y-1">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {isTyping && <ChatTypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  )
}
