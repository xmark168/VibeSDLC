import { cn } from "@/lib/utils";
import { Loader2, CheckCircle2, Clock, AlertCircle } from "lucide-react";

export type AgentStatus = 'idle' | 'thinking' | 'acting' | 'waiting' | 'error';

interface AgentStatusIndicatorProps {
  status: AgentStatus;
  agentName?: string;
  currentAction?: string;
  currentStep?: number;
  totalSteps?: number;
  executionId?: string;
  className?: string;
}

const statusConfig = {
  idle: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-900',
    borderColor: 'border-gray-200 dark:border-gray-800',
    label: 'Idle'
  },
  thinking: {
    icon: Loader2,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950',
    borderColor: 'border-purple-200 dark:border-purple-800',
    label: 'Thinking',
    animate: true
  },
  acting: {
    icon: Loader2,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950',
    borderColor: 'border-blue-200 dark:border-blue-800',
    label: 'Processing',
    animate: true
  },
  waiting: {
    icon: Clock,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
    label: 'Waiting'
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950',
    borderColor: 'border-red-200 dark:border-red-800',
    label: 'Error'
  }
};

export function AgentStatusIndicator({
  status,
  agentName,
  currentAction,
  currentStep,
  totalSteps,
  executionId,
  className
}: AgentStatusIndicatorProps) {
  const config = statusConfig[status];
  const Icon = config.icon;
  
  // Calculate progress percentage
  const progressPercentage = currentStep && totalSteps ? (currentStep / totalSteps) * 100 : 0;
  const hasProgress = currentStep && totalSteps && currentStep > 0;

  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-2 rounded-lg border transition-all",
      config.bgColor,
      config.borderColor,
      className
    )}>
      {/* Status Icon */}
      <Icon 
        className={cn(
          "h-4 w-4 flex-shrink-0",
          config.color,
          config.animate && "animate-spin"
        )} 
      />

      {/* Agent Name */}
      <span className={cn("text-sm font-medium", config.color)}>
        {agentName || 'Agent'}
      </span>

      {/* Separator */}
      {currentAction && <span className="text-gray-400 dark:text-gray-600">•</span>}

      {/* Current Action */}
      {currentAction && (
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {currentAction}
        </span>
      )}

      {/* Progress Indicator */}
      {hasProgress && (
        <>
          <span className="text-gray-400 dark:text-gray-600">•</span>
          <div className="flex items-center gap-1.5">
            {/* Mini Progress Bar */}
            <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full transition-all duration-300",
                  config.color.replace('text-', 'bg-')
                )}
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            {/* Step Counter */}
            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              {currentStep}/{totalSteps}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// Compact version for inline use
export function AgentStatusDot({
  status,
  className
}: {
  status: AgentStatus;
  className?: string
}) {
  const config = statusConfig[status];

  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      {status === 'thinking' && (
        <div className={cn(
          "absolute w-4 h-4 rounded-full animate-ping",
          config.ringColor
        )} />
      )}
      <div className={cn(
        "w-2 h-2 rounded-full relative z-10",
        config.color,
        config.animation
      )} />
    </div>
  );
}
