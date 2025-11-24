/**
 * MessageInput - Chat message input with mentions support
 * 
 * Features:
 * - Auto-resizing textarea
 * - Agent mention trigger (@)
 * - Keyboard shortcuts (Enter to send, Shift+Enter for newline)
 * - Character/line limits
 * - Disabled state during sending
 */

import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ArrowUp } from 'lucide-react'

export interface MessageInputProps {
  /** Current message value */
  value: string
  /** Value change handler */
  onChange: (value: string) => void
  /** Send message handler */
  onSend: () => void
  /** Mention trigger handler (when @ is typed) */
  onMentionTrigger?: (search: string) => void
  /** Disabled state (e.g. while sending) */
  disabled?: boolean
  /** Placeholder text */
  placeholder?: string
  /** Show character count */
  showCharCount?: boolean
  /** Max characters */
  maxChars?: number
}

export function MessageInput({
  value,
  onChange,
  onSend,
  onMentionTrigger,
  disabled = false,
  placeholder = "Type your message...",
  showCharCount = false,
  maxChars = 5000,
}: MessageInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [isFocused, setIsFocused] = useState(false)

  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    // Reset height to recalculate
    textarea.style.height = 'auto'
    
    // Set new height based on scroll height (max 200px)
    const newHeight = Math.min(textarea.scrollHeight, 200)
    textarea.style.height = `${newHeight}px`
  }, [value])

  // Handle input change
  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value

    // Check for @ mention trigger
    if (onMentionTrigger) {
      const cursorPosition = e.target.selectionStart
      const textBeforeCursor = newValue.slice(0, cursorPosition)
      const mentionMatch = textBeforeCursor.match(/@(\w*)$/)
      
      if (mentionMatch) {
        // User typed @ - trigger mention dropdown
        onMentionTrigger(mentionMatch[1]) // Search query after @
      }
    }

    onChange(newValue)
  }

  // Handle keyboard shortcuts
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send (Shift+Enter for newline)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled) {
        onSend()
      }
    }
  }

  // Handle send button click
  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend()
    }
  }

  // Check if can send
  const canSend = value.trim().length > 0 && !disabled

  return (
    <div className="border-t bg-background p-4">
      <div className="relative flex items-end gap-2">
        {/* Textarea */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            className="min-h-[60px] max-h-[200px] resize-none pr-12"
            rows={1}
          />
          
          {/* Character count */}
          {showCharCount && (
            <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
              {value.length}/{maxChars}
            </div>
          )}
        </div>

        {/* Send button */}
        <Button
          onClick={handleSend}
          disabled={!canSend}
          size="icon"
          className="h-10 w-10 shrink-0"
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>

      {/* Helper text */}
      <div className="mt-2 text-xs text-muted-foreground">
        <span>Press Enter to send, Shift+Enter for new line</span>
        {onMentionTrigger && <span className="ml-2">• Type @ to mention an agent</span>}
      </div>
    </div>
  )
}
