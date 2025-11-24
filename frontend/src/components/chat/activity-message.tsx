import { useEffect, useState } from 'react'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import type { Message } from '@/types/message'

interface ActivityMessageProps {
  message: Message
  onComplete?: () => void
}

interface ActivityStep {
  step: number
  description: string
  status: 'in_progress' | 'completed' | 'failed'
  timestamp: string
}

interface ActivityData {
  execution_id: string
  agent_name: string
  total_steps?: number
  current_step?: number
  steps?: ActivityStep[]
  events?: any[]  // Backend may send "events" instead of "steps"
  status: 'in_progress' | 'completed' | 'failed' | 'running' | 'success'
  started_at: string
  completed_at?: string | null
  finished_at?: string | null
}

export function ActivityMessage({ message, onComplete }: ActivityMessageProps) {
  // Support both structured_data.data and structured_data directly
  const activityData = (message.structured_data?.data || message.structured_data) as ActivityData | undefined
  const [isVisible, setIsVisible] = useState(true)

  if (!activityData || !isVisible) {
    return null
  }

  // Use events as steps if steps not provided
  const steps = activityData.steps || activityData.events || []
  const totalSteps = activityData.total_steps || steps.length || 0
  const currentStep = activityData.current_step || steps.length || 0

  const progressPercentage = totalSteps > 0
    ? (currentStep / totalSteps) * 100
    : 0

  const isCompleted = activityData.status === 'completed' || activityData.status === 'success'
  const isFailed = activityData.status === 'failed'
  const isInProgress = activityData.status === 'in_progress' || activityData.status === 'running'

  // Get current step description (safely handle undefined steps)
  const currentStepData = steps?.find((s: any) => s.status === 'in_progress' || s.status === 'running')
  const currentStepDesc = currentStepData?.description || currentStepData?.event_type || currentStepData?.type ||
    (isCompleted ? 'Complete' : isFailed ? 'Failed' : 'Processing...')

  // Auto-hide completed activities after 3 seconds
  useEffect(() => {
    if (isCompleted && onComplete) {
      const timer = setTimeout(() => {
        setIsVisible(false)
        onComplete()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isCompleted, onComplete])

  return (
    <div className="my-1">
      <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
        isCompleted
          ? 'bg-green-50 border border-green-200 dark:bg-green-950 dark:border-green-800'
          : isFailed
          ? 'bg-red-50 border border-red-200 dark:bg-red-950 dark:border-red-800'
          : 'bg-blue-50 border border-blue-200 dark:bg-blue-950 dark:border-blue-800'
      }`}>
        {/* Status Icon */}
        {isCompleted ? (
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0" />
        ) : isFailed ? (
          <XCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0" />
        ) : (
          <Loader2 className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0" />
        )}

        {/* Agent Name */}
        <span className={`text-sm font-medium ${
          isCompleted
            ? 'text-green-700 dark:text-green-300'
            : isFailed
            ? 'text-red-700 dark:text-red-300'
            : 'text-blue-700 dark:text-blue-300'
        }`}>
          {activityData.agent_name}
        </span>

        {/* Separator */}
        <span className="text-gray-400 dark:text-gray-600">•</span>

        {/* Current Step Description */}
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {currentStepDesc}
        </span>

        {/* Progress Indicator */}
        {isInProgress && (
          <>
            <span className="text-gray-400 dark:text-gray-600">•</span>
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                {currentStep}/{totalSteps}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
