import { useState, useEffect } from 'react'
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
import { Loader2 } from 'lucide-react'
import { ColorPicker } from '@/shared/components/ColorPicker'
import { IconPicker } from '@/shared/components/IconPicker'
import { KanbanConfigSection } from './KanbanConfigSection'
import type { Project, CreateProjectData, UpdateProjectData, KanbanPolicy } from '@/features/projects/types'
import { DEFAULT_KANBAN_POLICY, PROJECT_COLORS } from '@/features/projects/types'
import { projectsAPI } from '@/features/projects/api/projects'
import { toast } from 'sonner'

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
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto glass-premium">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            {isEditMode ? 'Edit Project' : 'Create New Project'}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? 'Update your project details and Kanban configuration'
              : 'Set up a new project with custom workflow and WIP limits'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2 glass">
              <TabsTrigger value="basic" className="data-[state=active]:bg-white/60">
                Basic Info
              </TabsTrigger>
              <TabsTrigger value="kanban" className="data-[state=active]:bg-white/60">
                Kanban Config
              </TabsTrigger>
            </TabsList>

            {/* Tab 1: Basic Info */}
            <TabsContent value="basic" className="space-y-6 mt-6">
              {/* Project Code */}
              <div className="space-y-2">
                <Label htmlFor="code" className="text-sm font-semibold">
                  Project Code <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="code"
                  {...register('code')}
                  placeholder="e.g., PROJ-001, WEB-APP"
                  className="bg-white/50 backdrop-blur-xl border-white/30"
                  disabled={isEditMode} // Code cannot be changed after creation
                />
                {errors.code && <p className="text-sm text-red-600">{errors.code.message}</p>}
                <p className="text-xs text-muted-foreground">
                  Unique identifier for this project {isEditMode && '(cannot be changed)'}
                </p>
              </div>

              {/* Project Name */}
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-semibold">
                  Project Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="name"
                  {...register('name')}
                  placeholder="e.g., E-commerce Platform, Mobile App"
                  className="bg-white/50 backdrop-blur-xl border-white/30"
                />
                {errors.name && <p className="text-sm text-red-600">{errors.name.message}</p>}
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm font-semibold">
                  Description
                </Label>
                <Textarea
                  id="description"
                  {...register('description')}
                  placeholder="Brief description of the project..."
                  rows={4}
                  className="bg-white/50 backdrop-blur-xl border-white/30 resize-none"
                />
                {errors.description && <p className="text-sm text-red-600">{errors.description.message}</p>}
              </div>

              {/* Color Picker */}
              <ColorPicker value={selectedColor} onChange={(color) => setValue('color', color)} />

              {/* Icon Picker */}
              <IconPicker value={selectedIcon} onChange={(icon) => setValue('icon', icon)} />
            </TabsContent>

            {/* Tab 2: Kanban Configuration */}
            <TabsContent value="kanban" className="space-y-6 mt-6">
              <KanbanConfigSection kanbanPolicy={kanbanPolicy} onChange={setKanbanPolicy} />
            </TabsContent>
          </Tabs>

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
            >
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditMode ? 'Update Project' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
