/**
 * Background Tasks Panel
 * 
 * Displays progress for background tasks (non-interactive agent operations)
 * Shows in a Sheet/Drawer with progress bars for each task
 */

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import type { BackgroundTask } from '@/types'
import { Loader2, Check, X } from 'lucide-react'

interface BackgroundTasksPanelProps {
  tasks: Map<string, BackgroundTask>
}

export function BackgroundTasksPanel({ tasks }: BackgroundTasksPanelProps) {
  const taskArray = Array.from(tasks.values())
  const inProgressCount = taskArray.filter(t => t.status === 'in_progress').length

  if (taskArray.length === 0) {
    return null
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="relative">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Background Tasks
          {inProgressCount > 0 && (
            <Badge variant="secondary" className="ml-2">
              {inProgressCount}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle>Background Tasks</SheetTitle>
          <SheetDescription>
            Tasks running in the background
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {taskArray.map((task) => (
            <TaskItem key={task.task_id} task={task} />
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

interface TaskItemProps {
  task: BackgroundTask
}

function TaskItem({ task }: TaskItemProps) {
  const StatusIcon = {
    in_progress: Loader2,
    completed: Check,
    failed: X,
  }[task.status] as typeof Loader2

  const statusColor = {
    in_progress: 'text-blue-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
  }[task.status] as string

  const statusText = {
    in_progress: 'In Progress',
    completed: 'Completed',
    failed: 'Failed',
  }[task.status] as string

  return (
    <div className="space-y-2 rounded-lg border p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon
            className={`h-4 w-4 ${statusColor} ${task.status === 'in_progress' ? 'animate-spin' : ''}`}
          />
          <span className="font-medium text-sm">{task.agent_name}</span>
        </div>
        <Badge variant={task.status === 'completed' ? 'default' : 'secondary'}>
          {statusText}
        </Badge>
      </div>

      {/* Progress Bar */}
      <Progress value={task.percentage} className="h-2" />

      {/* Details */}
      <div className="space-y-1 text-sm">
        <div className="flex justify-between text-muted-foreground">
          <span>
            {task.current} / {task.total}
          </span>
          <span>{Math.round(task.percentage)}%</span>
        </div>
        <p className="text-xs text-muted-foreground">{task.message}</p>
      </div>

      {/* Timestamp */}
      <p className="text-xs text-muted-foreground">
        Updated {new Date(task.updated_at).toLocaleTimeString()}
      </p>
    </div>
  )
}
