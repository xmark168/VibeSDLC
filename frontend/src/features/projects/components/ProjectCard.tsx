import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreVertical, Edit, Trash2, FolderKanban, ListTodo, Calendar } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.jsx'
import { Button } from '@/shared/ui/button'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog.jsx'
import type { Project } from '@/features/projects/types'
import { getIconByName } from '@/shared/components/IconPicker'
import { cn } from '@/lib/utils'
import { projectsAPI } from '@/features/projects/api/projects'
import { toast } from 'sonner'
import { format } from 'date-fns'

interface ProjectCardProps {
  project: Project
  onEdit: (project: Project) => void
  onDelete: () => void
}

export const ProjectCard = ({ project, onEdit, onDelete }: ProjectCardProps) => {
  const navigate = useNavigate()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const Icon = getIconByName(project.icon)
  const projectColor = project.color || '#3B82F6'

  const handleDelete = async () => {
    try {
      setIsDeleting(true)
      await projectsAPI.deleteProject(project.id)
      toast.success('Project deleted successfully')
      onDelete()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete project')
    } finally {
      setIsDeleting(false)
      setShowDeleteDialog(false)
    }
  }

  const handleCardClick = () => {
    navigate(`/projects/${project.id}`)
  }

  return (
    <>
      <div
        className="group glass-premium hover:scale-105 transition-all duration-500 cursor-pointer relative overflow-hidden shine"
        onClick={handleCardClick}
      >
        {/* Color accent bar */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r" style={{ background: `linear-gradient(to right, ${projectColor}, ${projectColor}88)` }}></div>

        {/* Gradient border effect on hover */}
        <div
          className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl"
          style={{ background: `linear-gradient(135deg, ${projectColor}20, transparent)` }}
        ></div>

        <div className="relative p-6 space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1">
              {/* Icon */}
              <div
                className="p-3 rounded-xl shadow-lg group-hover:shadow-2xl group-hover:scale-110 transition-all duration-300"
                style={{ backgroundColor: `${projectColor}20` }}
              >
                <Icon className="h-6 w-6" style={{ color: projectColor }} />
              </div>

              {/* Project info */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-xl text-foreground group-hover:text-blue-600 transition-colors duration-300 truncate">
                  {project.name}
                </h3>
                <p className="text-xs text-muted-foreground font-mono mt-0.5">{project.code}</p>
              </div>
            </div>

            {/* Actions dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 hover:bg-white/40"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="glass-premium">
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit(project)
                  }}
                  className="cursor-pointer"
                >
                  <Edit className="mr-2 h-4 w-4 text-blue-600" />
                  <span>Edit</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowDeleteDialog(true)
                  }}
                  className="cursor-pointer text-red-600 focus:text-red-700"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  <span>Delete</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Description */}
          {project.description && (
            <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
              {project.description}
            </p>
          )}

          {/* Progress bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-muted-foreground">Progress</span>
              <span
                className="font-bold"
                style={{ color: projectColor }}
              >
                {Math.round(project.progress || 0)}%
              </span>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{
                  width: `${project.progress || 0}%`,
                  backgroundColor: projectColor,
                }}
              ></div>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${projectColor}15` }}>
                <ListTodo className="h-3.5 w-3.5" style={{ color: projectColor }} />
              </div>
              <span className="text-xs font-medium text-muted-foreground">
                {project.active_stories_count || 0} active stories
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              <span>{format(new Date(project.created_at), 'MMM dd, yyyy')}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="glass-premium">
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the project <strong>{project.name}</strong> and all its data.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
