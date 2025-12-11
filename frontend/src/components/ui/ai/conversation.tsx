'use client'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { ArrowDownIcon } from 'lucide-react'
import type { HTMLAttributes } from 'react'
import { useRef, useEffect, useState, useCallback, createContext, useContext } from 'react'

// Context for scroll state
const ConversationContext = createContext<{
  scrollRef: React.RefObject<HTMLDivElement> | null
  isAtBottom: boolean
  scrollToBottom: () => void
}>({
  scrollRef: null,
  isAtBottom: true,
  scrollToBottom: () => {},
})

export type ConversationProps = HTMLAttributes<HTMLDivElement>

export const Conversation = ({ className, children, ...props }: ConversationProps) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  const checkIfAtBottom = useCallback(() => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50)
    }
  }, [])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [])

  // Auto-scroll when children change if already at bottom
  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom()
    }
  }, [children, isAtBottom, scrollToBottom])

  return (
    <ConversationContext.Provider value={{ scrollRef, isAtBottom, scrollToBottom }}>
      <div
        ref={scrollRef}
        className={cn('relative flex-1 overflow-y-auto', className)}
        onScroll={checkIfAtBottom}
        role="log"
        {...props}
      >
        {children}
      </div>
    </ConversationContext.Provider>
  )
}

export type ConversationContentProps = HTMLAttributes<HTMLDivElement>

export const ConversationContent = ({
  className,
  ...props
}: ConversationContentProps) => (
  <div className={cn('px-4 py-2', className)} {...props} />
)

export type ConversationScrollButtonProps = HTMLAttributes<HTMLButtonElement>

export const ConversationScrollButton = ({
  className,
  ...props
}: ConversationScrollButtonProps) => {
  const { isAtBottom, scrollToBottom } = useContext(ConversationContext)

  if (isAtBottom) return null

  return (
    <Button
      className={cn(
        'absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full shadow-lg z-10',
        className
      )}
      onClick={scrollToBottom}
      size="sm"
      type="button"
      variant="secondary"
      {...(props as any)}
    >
      <ArrowDownIcon className="size-4 mr-1" />
      New messages
    </Button>
  )
}
