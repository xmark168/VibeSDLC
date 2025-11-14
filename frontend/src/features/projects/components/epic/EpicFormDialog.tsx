import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { X, Loader2, AlertCircle } from 'lucide-react'
import { projectsAPI, type CreateEpicData, type UpdateEpicData } from '../../api/projects'
import type { Epic } from '../../types/epic'
import { toast } from 'sonner'

interface EpicFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  epic?: Epic | null
  projectId: number
  onSuccess?: () => void
}

interface EpicFormData {
  title: string
  description: string
}

export const EpicFormDialog = ({ open, onOpenChange, epic, projectId, onSuccess }: EpicFormDialogProps) => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isEditMode = !!epic

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EpicFormData>({
    defaultValues: {
      title: '',
      description: '',
    },
  })

  // Reset form when dialog opens/closes or epic changes
  useEffect(() => {
    if (open) {
      reset({
        title: epic?.title || '',
        description: epic?.description || '',
      })
      setError(null)
    } else {
      reset({
        title: '',
        description: '',
      })
      setError(null)
    }
  }, [open, epic, reset])

  const onSubmit = async (data: EpicFormData) => {
    try {
      setIsSubmitting(true)
      setError(null)

      if (isEditMode && epic) {
        // Update existing epic
        const updateData: UpdateEpicData = {
          title: data.title,
          description: data.description || undefined,
        }
        await projectsAPI.updateEpic(epic.id, updateData)
        toast.success('Epic updated successfully!')
      } else {
        // Create new epic
        const createData: CreateEpicData = {
          title: data.title,
          description: data.description || undefined,
          project_id: projectId,
        }
        await projectsAPI.createEpic(createData)
        toast.success('Epic created successfully!')
      }

      onOpenChange(false)
      onSuccess?.()
    } catch (err: any) {
      console.error(`Failed to ${isEditMode ? 'update' : 'create'} epic:`, err)
      const errorMessage = err.response?.data?.detail || err.message || `Failed to ${isEditMode ? 'update' : 'create'} epic`
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>{isEditMode ? 'Edit Epic' : 'Create New Epic'}</DialogTitle>
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
              placeholder="Enter epic title..."
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
              placeholder="Describe the epic in detail..."
              rows={6}
              {...register('description')}
              className="border-2 resize-none"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500">
              An epic is a large body of work that can be broken down into smaller stories
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
                  {isEditMode ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                isEditMode ? 'Update Epic' : 'Create Epic'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
