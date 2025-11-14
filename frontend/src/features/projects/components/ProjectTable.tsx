import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreHorizontal, Edit, Trash2, ExternalLink } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table.jsx'
import { Button } from '@/shared/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.jsx'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog.jsx'
import type { Project } from '@/features/projects/types'
import { getIconByName } from '@/shared/components/IconPicker'
import { projectsAPI } from '@/features/projects/api/projects'
import { toast } from 'sonner'
import { format } from 'date-fns'

interface ProjectTableProps {
  projects: Project[]
  onEdit: (project: Project) => void
  onDelete: () => void
}

export const ProjectTable = ({ projects, onEdit, onDelete }: ProjectTableProps) => {
  const navigate = useNavigate()
  const [deleteProject, setDeleteProject] = useState<Project | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async () => {
    if (!deleteProject) return

    try {
      setIsDeleting(true)
      await projectsAPI.deleteProject(deleteProject.id)
      toast.success('Project deleted successfully')
      onDelete()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete project')
    } finally {
      setIsDeleting(false)
      setDeleteProject(null)
    }
  }

  return (
    <>
      <div className="glass-premium rounded-xl overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-white/20 border-b border-white/20">
              <TableHead className="font-bold">Project</TableHead>
              <TableHead className="font-bold">Code</TableHead>
              <TableHead className="font-bold">Created</TableHead>
              <TableHead className="font-bold">Stories</TableHead>
              <TableHead className="font-bold">Progress</TableHead>
              <TableHead className="text-right font-bold">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects.map((project) => {
              const Icon = getIconByName(project.icon)
              const projectColor = project.color || '#3B82F6'

              return (
                <TableRow
                  key={project.id}
                  className="hover:bg-white/20 border-b border-white/10 cursor-pointer transition-colors"
                  onClick={() => navigate(`/projects/${project.id}`)}
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div
                        className="p-2 rounded-lg"
                        style={{ backgroundColor: `${projectColor}20` }}
                      >
                        <Icon className="h-4 w-4" style={{ color: projectColor }} />
                      </div>
                      <div>
                        <p className="font-semibold">{project.name}</p>
                        {project.description && (
                          <p className="text-xs text-muted-foreground line-clamp-1">
                            {project.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs px-2 py-1 rounded bg-slate-200 text-slate-700">
                      {project.code}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {format(new Date(project.created_at), 'MMM dd, yyyy')}
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold">{project.active_stories_count || 0}</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden max-w-[100px]">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${project.progress || 0}%`,
                            backgroundColor: projectColor,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium" style={{ color: projectColor }}>
                        {Math.round(project.progress || 0)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="glass-premium">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/projects/${project.id}`)
                          }}
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            onEdit(project)
                          }}
                        >
                          <Edit className="mr-2 h-4 w-4 text-blue-600" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeleteProject(project)
                          }}
                          className="text-red-600 focus:text-red-700"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteProject} onOpenChange={() => setDeleteProject(null)}>
        <AlertDialogContent className="glass-premium">
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the project <strong>{deleteProject?.name}</strong> and all its data. This action cannot be undone.
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
