import { useState, useEffect, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.jsx'
import { Button } from '@/shared/ui/button'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Loader2, Sparkles, Info, CheckCircle2, AlertCircle } from 'lucide-react'
import { ColorPicker } from '@/shared/components/ColorPicker'
import { IconPicker } from '@/shared/components/IconPicker'
import { KanbanConfigSection } from './KanbanConfigSection'
import type { Project, CreateProjectData, UpdateProjectData, KanbanPolicy } from '@/features/projects/types'
import { DEFAULT_KANBAN_POLICY, PROJECT_COLORS } from '@/features/projects/types'
import { projectsAPI } from '@/features/projects/api/projects'
import { toast } from 'sonner'

// Generate UUID v4
const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// Auto-generate project code from name with UUID
const generateProjectCode = (name: string): string => {
  if (!name) return generateUUID()

  // Take first letters of each word, max 3 words
  const words = name.trim().split(/\s+/).slice(0, 3)
  const prefix = words
    .map(word => word.charAt(0).toUpperCase())
    .join('')

  // Use short UUID (first 8 characters)
  const shortUUID = generateUUID().split('-')[0].toUpperCase()
  return `${prefix}-${shortUUID}`
}

// Form validation schema
const projectSchema = z.object({
  code: z.string().min(1, 'Project code is required').max(50, 'Code must be less than 50 characters'),
  name: z.string().min(1, 'Project name is required').max(255, 'Name must be less than 255 characters'),
  description: z.string().optional(),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Invalid hex color').optional(),
  icon: z.string().max(50).optional(),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface ProjectFormDialogProps {
  open: boolean
  onClose: () => void
  project?: Project | null // If provided, edit mode; otherwise create mode
  onSuccess?: () => void
}

export const ProjectFormDialog = ({ open, onClose, project, onSuccess }: ProjectFormDialogProps) => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [kanbanPolicy, setKanbanPolicy] = useState<KanbanPolicy>(
    project?.kanban_policy || DEFAULT_KANBAN_POLICY
  )
  const [activeTab, setActiveTab] = useState('basic')

  const isEditMode = !!project

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      code: project?.code || '',
      name: project?.name || '',
      description: project?.description || '',
      color: project?.color || PROJECT_COLORS[0],
      icon: project?.icon || 'folder-kanban',
    },
  })

  // Reset form when project changes or dialog opens
  useEffect(() => {
    if (open) {
      reset({
        code: project?.code || '',
        name: project?.name || '',
        description: project?.description || '',
        color: project?.color || PROJECT_COLORS[0],
        icon: project?.icon || 'folder-kanban',
      })
      setKanbanPolicy(project?.kanban_policy || DEFAULT_KANBAN_POLICY)
      setActiveTab('basic')
    }
  }, [open, project, reset])

  const selectedColor = watch('color')
  const selectedIcon = watch('icon')
  const watchedName = watch('name')

  // Auto-generate code when name changes (only for new projects)
  useEffect(() => {
    if (!isEditMode && watchedName) {
      const generatedCode = generateProjectCode(watchedName)
      setValue('code', generatedCode)
    }
  }, [watchedName, isEditMode, setValue])

  // Generate initial code on mount for new projects
  useEffect(() => {
    if (!isEditMode && open && !watch('code')) {
      const generatedCode = generateProjectCode(watchedName || '')
      setValue('code', generatedCode)
    }
  }, [open, isEditMode, watchedName, setValue, watch])

  // Check form completion status
  const formCompletionStatus = useMemo(() => {
    const watchedCode = watch('code')
    const hasBasicInfo = !!(watchedName && watchedCode)
    const hasDescription = !!watch('description')
    const hasCustomization = !!(selectedColor && selectedIcon)

    return {
      basic: hasBasicInfo,
      description: hasDescription,
      customization: hasCustomization,
      overall: hasBasicInfo && hasDescription && hasCustomization
    }
  }, [watchedName, watch('code'), watch('description'), selectedColor, selectedIcon])

  const onSubmit = async (data: ProjectFormData) => {
    try {
      setIsSubmitting(true)

      const projectData: CreateProjectData | UpdateProjectData = {
        code: data.code,
        name: data.name,
        description: data.description || undefined,
        color: data.color || undefined,
        icon: data.icon || undefined,
        kanban_policy: kanbanPolicy,
      }

      if (isEditMode) {
        await projectsAPI.updateProject(project.id, projectData)
        toast.success('Project updated successfully!')
      } else {
        await projectsAPI.createProject(projectData as CreateProjectData)
        toast.success('Project created successfully!')
      }

      onSuccess?.()
      onClose()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to save project'
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[92vh] overflow-hidden bg-white border-0 shadow-2xl p-0">
        <DialogHeader className="px-8 pt-8 pb-6 bg-gradient-to-br from-blue-50 via-white to-purple-50 border-b-2 border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="p-3.5 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-lg">
                <Sparkles className="h-7 w-7 text-white" />
              </div>
              <div className="space-y-2">
                <DialogTitle className="text-3xl font-bold text-gray-900">
                  {isEditMode ? 'Edit Project' : 'Create New Project'}
                </DialogTitle>
                <DialogDescription className="text-base text-gray-600 leading-relaxed">
                  {isEditMode
                    ? 'Update your project details and Kanban configuration'
                    : 'Set up a new project with custom workflow and WIP limits'}
                </DialogDescription>
              </div>
            </div>
            {!isEditMode && formCompletionStatus.overall && (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-green-500/10 border-2 border-green-500/30 rounded-xl shadow-sm">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <span className="text-sm font-semibold text-green-700">Ready</span>
              </div>
            )}
          </div>
        </DialogHeader>

        <div className="overflow-y-auto max-h-[calc(92vh-220px)] px-8 py-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2 bg-gray-100 p-1.5 h-auto rounded-xl">
                <TabsTrigger
                  value="basic"
                  className="data-[state=active]:bg-white data-[state=active]:shadow-md transition-all duration-200 py-3.5 px-6 text-base font-semibold rounded-lg data-[state=active]:text-gray-900 text-gray-600"
                >
                  <span className="flex items-center gap-2">
                    Basic Info
                    {formCompletionStatus.basic && (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    )}
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="kanban"
                  className="data-[state=active]:bg-white data-[state=active]:shadow-md transition-all duration-200 py-3.5 px-6 text-base font-semibold rounded-lg data-[state=active]:text-gray-900 text-gray-600"
                >
                  Kanban Config
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Basic Info */}
              <TabsContent value="basic" className="space-y-8 mt-8">
                {/* Project Name - Featured Field */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="name" className="text-lg font-bold text-gray-900">
                      Project Name <span className="text-red-500">*</span>
                    </Label>
                    <div className="group relative">
                      <Info className="h-4 w-4 text-gray-400 cursor-help hover:text-blue-500 transition-colors" />
                      <div className="hidden group-hover:block absolute left-0 top-7 z-50 w-72 p-4 bg-gray-900 text-white text-sm rounded-xl shadow-2xl">
                        <div className="font-semibold mb-1">Auto-generated Code</div>
                        Give your project a descriptive name. A unique code will be automatically generated using UUID.
                      </div>
                    </div>
                  </div>
                  <Input
                    id="name"
                    {...register('name')}
                    placeholder="e.g., E-commerce Platform, Mobile Banking App"
                    className="h-14 text-lg font-medium bg-white border-2 border-gray-200 focus:border-blue-500 rounded-xl transition-all shadow-sm hover:shadow-md focus:shadow-lg"
                    autoFocus
                  />
                  {errors.name && (
                    <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 px-4 py-3 rounded-lg">
                      <AlertCircle className="h-4 w-4 flex-shrink-0" />
                      <span>{errors.name.message}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-sm text-blue-700 bg-blue-50 px-4 py-2.5 rounded-lg border border-blue-100">
                    <Sparkles className="h-4 w-4 flex-shrink-0" />
                    <span>Unique code will be generated automatically using UUID</span>
                  </div>
                </div>

                {/* Description */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="description" className="text-base font-bold text-gray-900">
                      Description
                    </Label>
                    <span className="text-sm text-gray-500 font-medium">(Optional)</span>
                  </div>
                  <Textarea
                    id="description"
                    {...register('description')}
                    placeholder="Describe your project goals, target audience, and key features..."
                    rows={5}
                    className="resize-none bg-white border-2 border-gray-200 focus:border-blue-500 rounded-xl transition-all shadow-sm hover:shadow-md focus:shadow-lg text-base"
                  />
                  {errors.description && (
                    <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 px-4 py-3 rounded-lg">
                      <AlertCircle className="h-4 w-4 flex-shrink-0" />
                      <span>{errors.description.message}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">
                      {watch('description')?.length || 0} characters
                    </span>
                    {watch('description') && watch('description').length > 200 && (
                      <span className="text-blue-600 font-medium">Detailed description ✓</span>
                    )}
                  </div>
                </div>

                {/* Visual Customization Section */}
                <div className="space-y-6 p-8 bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-2xl border-2 border-gray-200">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Sparkles className="h-5 w-5 text-purple-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900">Visual Customization</h3>
                  </div>

                  {/* Color Picker */}
                  <div className="space-y-3">
                    <ColorPicker value={selectedColor} onChange={(color) => setValue('color', color)} />
                  </div>

                  {/* Icon Picker */}
                  <div className="space-y-3">
                    <IconPicker value={selectedIcon} onChange={(icon) => setValue('icon', icon)} />
                  </div>
                </div>
              </TabsContent>

              {/* Tab 2: Kanban Configuration */}
              <TabsContent value="kanban" className="space-y-6 mt-8">
                <KanbanConfigSection kanbanPolicy={kanbanPolicy} onChange={setKanbanPolicy} />
              </TabsContent>
            </Tabs>

            <DialogFooter className="gap-4 pt-6 pb-8 px-8 border-t-2 border-gray-100 bg-gray-50">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
                className="min-w-[120px] h-12 text-base font-semibold border-2 border-gray-300 hover:bg-gray-100 rounded-xl transition-all"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white min-w-[160px] h-12 text-base shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-[1.02] font-semibold rounded-xl"
              >
                {isSubmitting && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
                {isSubmitting ? 'Saving...' : isEditMode ? 'Update Project' : 'Create Project'}
              </Button>
            </DialogFooter>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  )
}
