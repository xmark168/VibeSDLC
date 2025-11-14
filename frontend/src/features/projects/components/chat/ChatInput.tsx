import { useState, useRef, KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSendMessage: (content: string) => void
  disabled?: boolean
  placeholder?: string
}

export const ChatInput = ({
  onSendMessage,
  disabled = false,
  placeholder = 'Type your message...',
}: ChatInputProps) => {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmedMessage = message.trim()
    if (!trimmedMessage || disabled) return

    onSendMessage(trimmedMessage)
    setMessage('')

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value)

    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
  }

  return (
    <div className="border-t-2 border-gray-200 bg-white p-4">
      <div className="flex items-end gap-3">
        {/* Textarea Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              'w-full resize-none rounded-xl border-2 border-gray-200 px-4 py-3 pr-12',
              'text-sm text-gray-900 placeholder:text-gray-400',
              'focus:border-blue-500 focus:outline-none focus:ring-0',
              'transition-colors duration-200',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'min-h-[48px] max-h-[120px]'
            )}
          />

          {/* Character hint */}
          {message.length > 0 && (
            <div className="absolute bottom-1 right-1 text-xs text-gray-400 bg-white px-1 rounded">
              {message.length}
            </div>
          )}
        </div>

        {/* Send Button */}
        <Button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          size="lg"
          className={cn(
            'h-12 w-12 rounded-xl flex-shrink-0',
            'bg-blue-500 hover:bg-blue-600 text-white',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-all duration-200',
            'shadow-md hover:shadow-lg'
          )}
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>

      {/* Helper Text */}
      <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
        <span>Press Enter to send, Shift + Enter for new line</span>
        {disabled && <span className="text-amber-600 font-medium">Agent is responding...</span>}
      </div>
    </div>
  )
}
