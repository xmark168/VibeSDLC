import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Button } from '@/components/ui/button.jsx'
import { X, Loader2, Plus, Pencil, Trash2, AlertCircle } from 'lucide-react'
import { projectsAPI } from '../../api/projects'
import type { Epic } from '../../types/epic'
import { EpicFormDialog } from './EpicFormDialog'
import { toast } from 'sonner'

interface EpicListDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: number
}

export const EpicListDialog = ({ open, onOpenChange, projectId }: EpicListDialogProps) => {
  const [epics, setEpics] = useState<Epic[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isEpicFormOpen, setIsEpicFormOpen] = useState(false)
  const [selectedEpic, setSelectedEpic] = useState<Epic | null>(null)
  const [deletingEpicId, setDeletingEpicId] = useState<number | null>(null)

  const loadEpics = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await projectsAPI.getEpicsByProject(projectId)
      // Filter out soft-deleted epics
      const activeEpics = data.filter(epic => !epic.deleted_at)
      setEpics(activeEpics)
    } catch (err: any) {
      console.error('Failed to load epics:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load epics'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadEpics()
    }
  }, [open, projectId])

  const handleCreateClick = () => {
    setSelectedEpic(null)
    setIsEpicFormOpen(true)
  }

  const handleEditClick = (epic: Epic) => {
    setSelectedEpic(epic)
    setIsEpicFormOpen(true)
  }

  const handleDeleteClick = async (epic: Epic) => {
    if (!confirm(`Are you sure you want to delete epic "${epic.title}"?`)) {
      return
    }

    try {
      setDeletingEpicId(epic.id)
      await projectsAPI.deleteEpic(epic.id)
      toast.success('Epic deleted successfully!')
      loadEpics()
    } catch (err: any) {
      console.error('Failed to delete epic:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete epic'
      toast.error(errorMessage)
    } finally {
      setDeletingEpicId(null)
    }
  }

  const handleEpicFormSuccess = () => {
    loadEpics()
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-bold">Manage Epics</DialogTitle>
              <div className="flex items-center gap-2">
                <Button onClick={handleCreateClick} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Epic
                </Button>
                <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-4">
            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            )}

            {/* Error State */}
            {error && !isLoading && (
              <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-red-900">Error</h4>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !error && epics.length === 0 && (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                  <Plus className="h-8 w-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Epics Yet</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Create your first epic to organize your stories
                </p>
                <Button onClick={handleCreateClick}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Epic
                </Button>
              </div>
            )}

            {/* Table View */}
            {!isLoading && !error && epics.length > 0 && (
              <div className="border-2 border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b-2 border-gray-200">
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Title
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Description
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider w-32">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {epics.map((epic) => (
                      <tr key={epic.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="text-sm font-semibold text-gray-900">{epic.title}</div>
                          <div className="text-xs text-gray-500 mt-1">ID: {epic.id}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-700 line-clamp-2">
                            {epic.description || (
                              <span className="text-gray-400 italic">No description</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditClick(epic)}
                              disabled={deletingEpicId === epic.id}
                            >
                              <Pencil className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(epic)}
                              disabled={deletingEpicId === epic.id}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              {deletingEpicId === epic.id ? (
                                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4 mr-1" />
                              )}
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Epic Count */}
            {!isLoading && !error && epics.length > 0 && (
              <div className="mt-4 text-sm text-gray-600 text-center">
                Showing {epics.length} epic{epics.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Epic Form Dialog */}
      <EpicFormDialog
        open={isEpicFormOpen}
        onOpenChange={setIsEpicFormOpen}
        epic={selectedEpic}
        projectId={projectId}
        onSuccess={handleEpicFormSuccess}
      />
    </>
  )
}
