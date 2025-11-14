import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.jsx'
import { X, Loader2, AlertCircle, Plus } from 'lucide-react'
import { StoryType, StoryPriority } from '../../types/project'
import { projectsAPI, type CreateStoryData } from '../../api/projects'
import type { Epic } from '../../types/epic'
import { EpicFormDialog } from '../epic/EpicFormDialog'
import { toast } from 'sonner'

interface StoryFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

interface StoryFormData {
  title: string
  description: string
  epic_id: number | null
  type: StoryType
  priority: StoryPriority
  acceptance_criteria: string
}

export const StoryFormDialog = ({ open, onOpenChange, onSuccess }: StoryFormDialogProps) => {
  const { id: projectId } = useParams<{ id: string }>()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [epics, setEpics] = useState<Epic[]>([])
  const [isLoadingEpics, setIsLoadingEpics] = useState(false)
  const [isEpicFormOpen, setIsEpicFormOpen] = useState(false)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<StoryFormData>({
    defaultValues: {
      title: '',
      description: '',
      epic_id: null,
      type: StoryType.USER_STORY,
      priority: StoryPriority.MEDIUM,
      acceptance_criteria: '',
    },
  })

  const selectedType = watch('type')
  const selectedPriority = watch('priority')
  const selectedEpicId = watch('epic_id')

  // Load epics when dialog opens
  useEffect(() => {
    if (open && projectId) {
      loadEpics()
    }
  }, [open, projectId])

  const loadEpics = async () => {
    if (!projectId) return

    try {
      setIsLoadingEpics(true)
      const data = await projectsAPI.getEpicsByProject(parseInt(projectId))
      // Filter out soft-deleted epics
      const activeEpics = data.filter(epic => !epic.deleted_at)
      setEpics(activeEpics)
    } catch (err: any) {
      console.error('Failed to load epics:', err)
      toast.error('Failed to load epics')
    } finally {
      setIsLoadingEpics(false)
    }
  }

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset()
      setError(null)
    }
  }, [open, reset])

  const onSubmit = async (data: StoryFormData) => {
    if (!projectId) {
      setError('Project ID is missing')
      return
    }

    if (!data.epic_id) {
      setError('Please select an Epic')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      const storyData: CreateStoryData = {
        title: data.title,
        description: data.description || undefined,
        epic_id: data.epic_id,
        type: data.type,
        priority: data.priority,
        acceptance_criteria: data.acceptance_criteria || undefined,
      }

      await projectsAPI.createStory(storyData)

      toast.success('Story created successfully!')
      onOpenChange(false)
      onSuccess?.()
    } catch (err: any) {
      console.error('Failed to create story:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create story'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEpicCreated = () => {
    loadEpics()
  }

  const STORY_TYPE_LABELS: Record<StoryType, { label: string; description: string }> = {
    [StoryType.USER_STORY]: {
      label: 'User Story',
      description: 'A feature or functionality from user perspective',
    },
    [StoryType.ENABLER_STORY]: {
      label: 'Enabler Story',
      description: 'Technical work that enables future features',
    },
  }

  const PRIORITY_LABELS: Record<StoryPriority, { label: string; color: string }> = {
    [StoryPriority.LOW]: { label: 'Low', color: 'text-gray-600' },
    [StoryPriority.MEDIUM]: { label: 'Medium', color: 'text-blue-600' },
    [StoryPriority.HIGH]: { label: 'High', color: 'text-orange-600' },
    [StoryPriority.CRITICAL]: { label: 'Critical', color: 'text-red-600' },
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>Create New Story</DialogTitle>
              <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 py-4">
          {/* Error Alert */}
          {error && (
            <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-red-900">Error</h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title" className="text-sm font-semibold text-gray-900">
              Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              placeholder="Enter story title..."
              {...register('title', {
                required: 'Title is required',
                minLength: { value: 1, message: 'Title must not be empty' },
                maxLength: { value: 255, message: 'Title must be less than 255 characters' },
              })}
              className="border-2"
              disabled={isSubmitting}
            />
            {errors.title && <p className="text-sm text-red-600">{errors.title.message}</p>}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-semibold text-gray-900">
              Description
            </Label>
            <Textarea
              id="description"
              placeholder="Describe the story in detail..."
              rows={4}
              {...register('description')}
              className="border-2 resize-none"
              disabled={isSubmitting}
            />
          </div>

          {/* Epic Selector */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-gray-900">
              Epic <span className="text-red-500">*</span>
            </Label>
            <div className="flex gap-2">
              <div className="flex-1">
                <Select
                  value={selectedEpicId?.toString() || ''}
                  onValueChange={(value) => setValue('epic_id', parseInt(value))}
                  disabled={isSubmitting || isLoadingEpics}
                >
                  <SelectTrigger className="border-2">
                    <SelectValue placeholder={isLoadingEpics ? 'Loading epics...' : 'Select an epic'} />
                  </SelectTrigger>
                  <SelectContent>
                    {epics.length === 0 && !isLoadingEpics && (
                      <div className="px-2 py-6 text-center text-sm text-gray-500">
                        No epics available. Create one first!
                      </div>
                    )}
                    {epics.map((epic) => (
                      <SelectItem key={epic.id} value={epic.id.toString()}>
                        <div className="flex flex-col items-start">
                          <span className="font-medium">{epic.title}</span>
                          {epic.description && (
                            <span className="text-xs text-gray-500 line-clamp-1">{epic.description}</span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setIsEpicFormOpen(true)}
                disabled={isSubmitting || isLoadingEpics}
                title="Create new epic"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Select the epic this story belongs to, or create a new one
            </p>
          </div>

          {/* Type and Priority Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Story Type */}
            <div className="space-y-2">
              <Label className="text-sm font-semibold text-gray-900">
                Story Type <span className="text-red-500">*</span>
              </Label>
              <Select value={selectedType} onValueChange={(value) => setValue('type', value as StoryType)}>
                <SelectTrigger className="border-2" disabled={isSubmitting}>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(StoryType).map((type) => (
                    <SelectItem key={type} value={type}>
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{STORY_TYPE_LABELS[type].label}</span>
                        <span className="text-xs text-gray-500">{STORY_TYPE_LABELS[type].description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <Label className="text-sm font-semibold text-gray-900">
                Priority <span className="text-red-500">*</span>
              </Label>
              <Select
                value={selectedPriority}
                onValueChange={(value) => setValue('priority', value as StoryPriority)}
              >
                <SelectTrigger className="border-2" disabled={isSubmitting}>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(StoryPriority).map((priority) => (
                    <SelectItem key={priority} value={priority}>
                      <span className={`font-medium ${PRIORITY_LABELS[priority].color}`}>
                        {PRIORITY_LABELS[priority].label}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Acceptance Criteria */}
          <div className="space-y-2">
            <Label htmlFor="acceptance_criteria" className="text-sm font-semibold text-gray-900">
              Acceptance Criteria
            </Label>
            <Textarea
              id="acceptance_criteria"
              placeholder="Define the conditions that must be met for this story to be considered complete..."
              rows={5}
              {...register('acceptance_criteria')}
              className="border-2 resize-none"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500">
              List the specific conditions that must be met for this story to be marked as complete
            </p>
          </div>

          {/* Info Note */}
          <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-3">
            <p className="text-sm text-blue-900">
              All new stories will be created with status: <span className="font-semibold">TODO</span>
            </p>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t-2 border-gray-200">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="min-w-[120px]">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Story'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>

    {/* Epic Form Dialog for Quick Create */}
    <EpicFormDialog
      open={isEpicFormOpen}
      onOpenChange={setIsEpicFormOpen}
      projectId={parseInt(projectId || '0')}
      onSuccess={handleEpicCreated}
    />
    </>
  )
}
