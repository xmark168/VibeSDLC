'use client'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { ComponentProps, HTMLAttributes } from 'react'

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: 'user' | 'assistant'
}

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      'group flex w-full items-start gap-3 py-2',
      from === 'user' ? 'is-user flex-row-reverse' : 'is-assistant',
      className
    )}
    {...props}
  />
)

export type MessageContentProps = HTMLAttributes<HTMLDivElement>

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      'flex flex-col gap-1 overflow-hidden rounded-2xl px-4 py-2.5 text-sm max-w-[85%]',
      'group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground',
      'group-[.is-assistant]:bg-muted group-[.is-assistant]:text-foreground',
      className
    )}
    {...props}
  >
    {children}
  </div>
)

export type MessageAvatarProps = ComponentProps<typeof Avatar> & {
  src?: string
  name?: string
  fallback?: React.ReactNode
}

export const MessageAvatar = ({
  src,
  name,
  fallback,
  className,
  ...props
}: MessageAvatarProps) => (
  <Avatar
    className={cn('size-8 shrink-0', className)}
    {...props}
  >
    {src && <AvatarImage alt={name || ''} src={src} />}
    <AvatarFallback className="text-xs">
      {fallback || name?.slice(0, 2).toUpperCase() || '??'}
    </AvatarFallback>
  </Avatar>
)

export type MessageHeaderProps = HTMLAttributes<HTMLDivElement>

export const MessageHeader = ({
  className,
  ...props
}: MessageHeaderProps) => (
  <div
    className={cn('flex items-center gap-2 text-xs text-muted-foreground mb-1', className)}
    {...props}
  />
)

export type MessageActionsProps = HTMLAttributes<HTMLDivElement>

export const MessageActions = ({
  className,
  ...props
}: MessageActionsProps) => (
  <div
    className={cn(
      'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity',
      className
    )}
    {...props}
  />
)
