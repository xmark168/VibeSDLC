import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Separator } from '@/components/ui/separator.jsx'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Calendar, AlertCircle } from 'lucide-react'
import type { Story } from '../../types/board'

interface StoryDetailDialogProps {
  story: Story | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PRIORITY_COLORS = {
  HIGH: 'bg-red-100 text-red-700 border-red-300',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-300',
  LOW: 'bg-blue-100 text-blue-700 border-blue-300',
  NONE: 'bg-gray-100 text-gray-700 border-gray-300',
}

const TYPE_COLORS = {
  USER_STORY: 'bg-blue-100 text-blue-700 border-blue-300',
  ENABLER_STORY: 'bg-purple-100 text-purple-700 border-purple-300',
  BUG: 'bg-red-100 text-red-700 border-red-300',
}

const STATUS_COLORS = {
  TODO: 'bg-gray-100 text-gray-700 border-gray-300',
  IN_PROGRESS: 'bg-blue-100 text-blue-700 border-blue-300',
  REVIEW: 'bg-purple-100 text-purple-700 border-purple-300',
  TESTING: 'bg-amber-100 text-amber-700 border-amber-300',
  DONE: 'bg-green-100 text-green-700 border-green-300',
  BLOCKED: 'bg-red-100 text-red-700 border-red-300',
  ARCHIVED: 'bg-slate-100 text-slate-700 border-slate-300',
}

export const StoryDetailDialog = ({ story, open, onOpenChange }: StoryDetailDialogProps) => {
  if (!story) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <DialogTitle className="text-xl">{story.title}</DialogTitle>
              <p className="text-sm text-gray-500 mt-1">Story #{story.id}</p>
            </div>
            {story.story_points && (
              <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                <span className="text-lg font-bold text-blue-700">{story.story_points}</span>
              </div>
            )}
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Badges */}
          <div className="flex flex-wrap gap-2">
            <Badge className={PRIORITY_COLORS[story.priority]}>
              {story.priority}
            </Badge>
            <Badge className={TYPE_COLORS[story.story_type]}>
              {story.story_type?.replace('_', ' ') || story.story_type}
            </Badge>
            <Badge className={STATUS_COLORS[story.status]}>
              {story.status?.replace('_', ' ') || story.status}
            </Badge>
          </div>

          <Separator />

          {/* Description */}
          {story.description && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Description</h4>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{story.description}</p>
            </div>
          )}

          {/* Acceptance Criteria */}
          {story.acceptance_criteria && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Acceptance Criteria</h4>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{story.acceptance_criteria}</p>
            </div>
          )}

          {/* Blocked Reason */}
          {story.blocked_reason && (
            <div className="p-4 bg-red-50 border-2 border-red-200 rounded-xl">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-red-900 mb-1">Blocked</h4>
                  <p className="text-sm text-red-700">{story.blocked_reason}</p>
                  {story.blocked_at && (
                    <p className="text-xs text-red-600 mt-1">
                      Since {format(new Date(story.blocked_at), 'PPp', { locale: vi })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          <Separator />

          {/* Timestamps */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700">Timeline</h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="h-4 w-4" />
                <div>
                  <p className="text-xs text-gray-500">Created</p>
                  <p className="font-medium">{format(new Date(story.created_at), 'PP', { locale: vi })}</p>
                </div>
              </div>
              {story.started_at && (
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="h-4 w-4" />
                  <div>
                    <p className="text-xs text-gray-500">Started</p>
                    <p className="font-medium">{format(new Date(story.started_at), 'PP', { locale: vi })}</p>
                  </div>
                </div>
              )}
              {story.completed_at && (
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="h-4 w-4" />
                  <div>
                    <p className="text-xs text-gray-500">Completed</p>
                    <p className="font-medium">{format(new Date(story.completed_at), 'PP', { locale: vi })}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
