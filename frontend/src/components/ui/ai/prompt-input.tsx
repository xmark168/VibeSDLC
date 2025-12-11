'use client'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { Loader2Icon, SendIcon, SquareIcon } from 'lucide-react'
import type { ComponentProps, HTMLAttributes, KeyboardEventHandler } from 'react'

export type PromptInputProps = HTMLAttributes<HTMLFormElement>

export const PromptInput = ({ className, ...props }: PromptInputProps) => (
  <form
    className={cn(
      'flex flex-col gap-2 rounded-xl border bg-background p-2 shadow-sm',
      className
    )}
    {...props}
  />
)

export type PromptInputTextareaProps = ComponentProps<typeof Textarea>

export const PromptInputTextarea = ({
  onChange,
  className,
  placeholder = 'Type a message...',
  ...props
}: PromptInputTextareaProps) => {
  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const form = e.currentTarget.form
      if (form) {
        form.requestSubmit()
      }
    }
  }

  return (
    <Textarea
      className={cn(
        'min-h-[44px] max-h-[200px] resize-none border-0 p-2 shadow-none',
        'focus-visible:ring-0 bg-transparent',
        className
      )}
      onChange={onChange}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      rows={1}
      {...props}
    />
  )
}

export type PromptInputToolbarProps = HTMLAttributes<HTMLDivElement>

export const PromptInputToolbar = ({
  className,
  ...props
}: PromptInputToolbarProps) => (
  <div
    className={cn('flex items-center justify-between', className)}
    {...props}
  />
)

export type PromptInputToolsProps = HTMLAttributes<HTMLDivElement>

export const PromptInputTools = ({
  className,
  ...props
}: PromptInputToolsProps) => (
  <div className={cn('flex items-center gap-1', className)} {...props} />
)

export type PromptInputButtonProps = ComponentProps<typeof Button>

export const PromptInputButton = ({
  variant = 'ghost',
  size = 'sm',
  className,
  ...props
}: PromptInputButtonProps) => (
  <Button
    className={cn('h-8 w-8 p-0 text-muted-foreground', className)}
    size={size}
    type="button"
    variant={variant}
    {...props}
  />
)

export type PromptInputSubmitProps = ComponentProps<typeof Button> & {
  isLoading?: boolean
  isStreaming?: boolean
}

export const PromptInputSubmit = ({
  className,
  size = 'sm',
  isLoading,
  isStreaming,
  children,
  ...props
}: PromptInputSubmitProps) => {
  let Icon = <SendIcon className="size-4" />

  if (isLoading) {
    Icon = <Loader2Icon className="size-4 animate-spin" />
  } else if (isStreaming) {
    Icon = <SquareIcon className="size-4" />
  }

  return (
    <Button
      className={cn('h-8 px-3', className)}
      size={size}
      type="submit"
      {...props}
    >
      {children ?? Icon}
    </Button>
  )
}
