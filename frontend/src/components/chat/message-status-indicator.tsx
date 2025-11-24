/**
 * MessageStatusIndicator - WhatsApp-like message status indicators
 * 
 * Shows message delivery status with icons:
 * - pending: Loading spinner
 * - sent: Single checkmark
 * - delivered: Double checkmarks
 * - failed: Error icon
 */

import { Check, CheckCheck, Loader2, AlertCircle } from "lucide-react"
import type { MessageStatus } from "@/types/message"

interface MessageStatusIndicatorProps {
  status?: MessageStatus
  className?: string
}

export function MessageStatusIndicator({ status, className = "" }: MessageStatusIndicatorProps) {
  if (!status) return null

  switch (status) {
    case 'pending':
      return (
        <Loader2 
          className={`w-3.5 h-3.5 animate-spin text-gray-400 ${className}`} 
          aria-label="Sending..."
        />
      )
    
    case 'sent':
      return (
        <Check 
          className={`w-3.5 h-3.5 text-gray-400 ${className}`}
          aria-label="Sent"
        />
      )
    
    case 'delivered':
      return (
        <CheckCheck 
          className={`w-3.5 h-3.5 text-gray-400 ${className}`}
          aria-label="Delivered"
        />
      )
    
    case 'failed':
      return (
        <AlertCircle 
          className={`w-3.5 h-3.5 text-red-500 ${className}`}
          aria-label="Failed to send"
        />
      )
    
    default:
      return null
  }
}
