import { cn } from "@/lib/utils";

export type AgentStatus = 'idle' | 'thinking' | 'acting' | 'waiting' | 'error';

interface AgentStatusIndicatorProps {
  status: AgentStatus;
  agentName?: string;
  currentAction?: string;
  className?: string;
}

const statusConfig = {
  idle: {
    color: 'bg-gray-400',
    ringColor: 'bg-gray-400/30',
    animation: '',
    label: 'Ready'
  },
  thinking: {
    color: 'bg-purple-500',
    ringColor: 'bg-purple-500/30',
    animation: 'animate-pulse',
    label: 'Thinking'
  },
  acting: {
    color: 'bg-blue-500',
    ringColor: 'bg-blue-500/30',
    animation: '',
    label: 'Processing'
  },
  waiting: {
    color: 'bg-yellow-500',
    ringColor: 'bg-yellow-500/30',
    animation: 'animate-bounce',
    label: 'Waiting for input'
  },
  error: {
    color: 'bg-red-500',
    ringColor: 'bg-red-500/30',
    animation: '',
    label: 'Error'
  }
};

export function AgentStatusIndicator({
  status,
  agentName,
  currentAction,
  className
}: AgentStatusIndicatorProps) {
  const config = statusConfig[status];

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative flex items-center justify-center">
        {/* Outer pulsing ring for thinking state */}
        {status === 'thinking' && (
          <div className={cn(
            "absolute w-5 h-5 rounded-full animate-ping",
            config.ringColor
          )} />
        )}
        {/* Inner dot */}
        <div className={cn(
          "w-3 h-3 rounded-full relative z-10",
          config.color,
          config.animation
        )} />
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground">
          {agentName || 'Agent'}: {config.label}
        </span>
        {currentAction && (
          <span className="text-xs text-muted-foreground">
            {currentAction}
          </span>
        )}
      </div>
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
