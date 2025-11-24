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

interface ActivityEvent {
  description: string
  details?: {
    milestone?: string
    [key: string]: any
  }
  timestamp: string
}

interface ActivityData {
  execution_id: string
  agent_name: string
  total_steps?: number
  current_step?: number
  steps?: ActivityStep[]
  events?: ActivityEvent[]
  status: 'in_progress' | 'completed' | 'failed'
  started_at: string
  completed_at: string | null
}

// Important milestones that should not auto-hide
const IMPORTANT_MILESTONES = new Set([
  'analysis_complete',
  'documentation_complete',
  'implementation_complete',
  'test_cases_complete',
  'scenarios_identified',
  'completed',
])

export function ActivityMessage({ message, onComplete }: ActivityMessageProps) {
  const activityData = message.structured_data?.data as ActivityData | undefined
  const [isVisible, setIsVisible] = useState(true)

  if (!activityData || !isVisible) {
    return null
  }

  const isCompleted = activityData.status === 'completed'
  const isFailed = activityData.status === 'failed'
  const isInProgress = activityData.status === 'in_progress'

  // Check if this activity has important milestones
  const hasImportantMilestone = activityData.events?.some(
    event => event.details?.milestone && IMPORTANT_MILESTONES.has(event.details.milestone)
  ) || false

  // Support both old step-based and new event-based format
  const events = activityData.events || []
  const steps = activityData.steps || []
  
  // Get current description
  let currentStepDesc = 'Processing...'
  if (events.length > 0) {
    // Event-based: use last event
    currentStepDesc = events[events.length - 1].description
  } else if (steps.length > 0) {
    // Step-based: use current step
    const currentStepData = steps.find(s => s.status === 'in_progress')
    currentStepDesc = currentStepData?.description || currentStepDesc
  }
  
  if (isCompleted) currentStepDesc = 'Complete'
  if (isFailed) currentStepDesc = 'Failed'

  // Calculate progress
  const progressPercentage = events.length > 0
    ? Math.min((events.length / 5) * 100, 100) // Assume ~5 events for 100%
    : (activityData.total_steps || 0) > 0
    ? ((activityData.current_step || 0) / (activityData.total_steps || 1)) * 100
    : 0

  // Auto-hide only if completed AND no important milestone
  useEffect(() => {
    if (isCompleted && !hasImportantMilestone && onComplete) {
      const timer = setTimeout(() => {
        setIsVisible(false)
        onComplete()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isCompleted, hasImportantMilestone, onComplete])

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
                {events.length > 0 ? `${events.length} events` : `${activityData.current_step}/${activityData.total_steps}`}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Event Timeline - show all events */}
      {events.length > 0 && (
        <div className="mt-2 ml-8 space-y-1">
          {events.map((event, idx) => (
            <div 
              key={idx} 
              className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400"
            >
              <span className="text-gray-400 mt-0.5">→</span>
              <span className="flex-1">{event.description}</span>
              {event.details?.milestone && (
                <span className="text-blue-500 font-medium">
                  {event.details.milestone}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
