import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, Loader2 } from 'lucide-react'
import type { Message } from '@/types/message'

interface ActivityMessageProps {
  message: Message
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
  total_steps: number
  current_step: number
  steps: ActivityStep[]
  status: 'in_progress' | 'completed' | 'failed'
  started_at: string
  completed_at: string | null
}

export function ActivityMessage({ message }: ActivityMessageProps) {
  const activityData = message.structured_data?.data as ActivityData | undefined

  // Auto-expand if in progress, auto-collapse if completed
  const [isExpanded, setIsExpanded] = useState(activityData?.status === 'in_progress')

  if (!activityData) {
    return null
  }

  const progressPercentage = activityData.total_steps > 0
    ? (activityData.current_step / activityData.total_steps) * 100
    : 0

  const isCompleted = activityData.status === 'completed'
  const isFailed = activityData.status === 'failed'

  return (
    <div className="my-2 max-w-2xl">
      <div
        className={`rounded-lg border ${
          isCompleted
            ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950'
            : isFailed
            ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950'
            : 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950'
        } p-3 shadow-sm`}
      >
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex w-full items-center justify-between text-left hover:opacity-80 transition-opacity"
        >
          <div className="flex items-center gap-2 flex-1">
            {/* Icon */}
            {isCompleted ? (
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            ) : isFailed ? (
              <div className="h-5 w-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs font-bold">!</span>
              </div>
            ) : (
              <Loader2 className="h-5 w-5 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0" />
            )}

            {/* Agent Name */}
            <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
              {activityData.agent_name}
            </span>

            {/* Status */}
            <span className={`text-sm font-medium ${
              isCompleted
                ? 'text-green-700 dark:text-green-300'
                : isFailed
                ? 'text-red-700 dark:text-red-300'
                : 'text-blue-700 dark:text-blue-300'
            }`}>
              {isCompleted ? 'Hoàn thành' : isFailed ? 'Lỗi' : 'Đang thực thi'}
            </span>

            {/* Progress */}
            <span className="text-xs text-gray-600 dark:text-gray-400 ml-auto mr-2">
              {activityData.current_step}/{activityData.total_steps}
            </span>
          </div>

          {/* Expand/Collapse Icon */}
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500 flex-shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500 flex-shrink-0" />
          )}
        </button>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="mt-3 space-y-2">
            {/* Steps List */}
            <div className="space-y-1.5">
              {activityData.steps.map((step, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-2 text-sm pl-7 ${
                    step.status === 'completed'
                      ? 'text-gray-600 dark:text-gray-400'
                      : step.status === 'in_progress'
                      ? 'text-gray-900 dark:text-gray-100 font-medium'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {/* Step Status Icon */}
                  <span className="flex-shrink-0 mt-0.5">
                    {step.status === 'completed' ? (
                      <span className="text-green-600 dark:text-green-400">✓</span>
                    ) : step.status === 'in_progress' ? (
                      <span className="text-blue-600 dark:text-blue-400">⏳</span>
                    ) : (
                      <span className="text-red-600 dark:text-red-400">✗</span>
                    )}
                  </span>

                  {/* Step Description */}
                  <div className="flex-1">
                    <span className="text-xs text-gray-500 dark:text-gray-500 mr-1.5">
                      Bước {step.step}/{activityData.total_steps}:
                    </span>
                    {step.description}
                  </div>
                </div>
              ))}
            </div>

            {/* Progress Bar */}
            <div className="mt-3 pl-7">
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    isCompleted
                      ? 'bg-green-500'
                      : isFailed
                      ? 'bg-red-500'
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 text-xs text-gray-500 dark:text-gray-400">
                <span>{Math.round(progressPercentage)}%</span>
                {activityData.completed_at && (
                  <span>
                    Hoàn thành lúc {new Date(activityData.completed_at).toLocaleTimeString('vi-VN')}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
