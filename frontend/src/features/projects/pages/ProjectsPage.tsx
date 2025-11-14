import { useState, useEffect } from 'react'
import { Plus, Grid3x3, TableIcon, Search, SlidersHorizontal, FolderKanban } from 'lucide-react'
import { Button } from '@/shared/ui/button'
import { Input } from '@/components/ui/input.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Skeleton } from '@/components/ui/skeleton.jsx'
import { ProjectCard } from '@/features/projects/components/ProjectCard'
import { ProjectTable } from '@/features/projects/components/ProjectTable'
import { ProjectFormDialog } from '@/features/projects/components/ProjectFormDialog'
import type { Project, ProjectViewMode } from '@/features/projects/types'
import { projectsAPI } from '@/features/projects/api/projects'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

export const ProjectsPage = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [filteredProjects, setFilteredProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<ProjectViewMode>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'created_at' | 'progress'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)

  // Fetch projects
  const fetchProjects = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await projectsAPI.getProjects()
      setProjects(data)
      setFilteredProjects(data)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load projects'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  // Apply filters and sorting
  useEffect(() => {
    let result = [...projects]

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.code.toLowerCase().includes(query) ||
          p.description?.toLowerCase().includes(query)
      )
    }

    // Sort
    result.sort((a, b) => {
      let compareA: any
      let compareB: any

      switch (sortBy) {
        case 'name':
          compareA = a.name.toLowerCase()
          compareB = b.name.toLowerCase()
          break
        case 'created_at':
          compareA = new Date(a.created_at).getTime()
          compareB = new Date(b.created_at).getTime()
          break
        case 'progress':
          compareA = a.progress || 0
          compareB = b.progress || 0
          break
        default:
          return 0
      }

      if (sortOrder === 'asc') {
        return compareA > compareB ? 1 : -1
      } else {
        return compareA < compareB ? 1 : -1
      }
    })

    setFilteredProjects(result)
  }, [projects, searchQuery, sortBy, sortOrder])

  const handleCreateSuccess = () => {
    fetchProjects()
    setShowCreateDialog(false)
  }

  const handleEditSuccess = () => {
    fetchProjects()
    setEditingProject(null)
  }

  const handleDeleteSuccess = () => {
    fetchProjects()
  }

  if (isLoading) {
    return (
      <div className="space-y-8 fade-in">
        <div className="space-y-3">
          <Skeleton className="h-12 w-80 glass-premium" />
          <Skeleton className="h-6 w-96 glass" />
        </div>
        <div className="flex gap-4">
          <Skeleton className="h-10 flex-1 glass" />
          <Skeleton className="h-10 w-40 glass" />
          <Skeleton className="h-10 w-32 glass" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-64 glass-premium" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fade-in">
        <div className="glass-premium p-12 text-center space-y-6">
          <div className="flex justify-center">
            <div className="p-6 bg-gradient-to-br from-red-500/20 to-orange-500/20 rounded-full backdrop-blur-xl">
              <svg className="h-16 w-16 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-red-600">Failed to load projects</h2>
            <p className="text-lg font-medium text-foreground">{error}</p>
          </div>
          <Button onClick={fetchProjects} className="bg-gradient-to-r from-blue-500 to-purple-600">
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  const hasProjects = projects.length > 0

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="space-y-3 fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-5xl font-bold gradient-text">Projects</h1>
            <p className="text-muted-foreground text-lg mt-2">
              {hasProjects
                ? `Manage your ${projects.length} project${projects.length !== 1 ? 's' : ''}`
                : 'Create your first project to get started'}
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            size="lg"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105"
          >
            <Plus className="h-5 w-5 mr-2" />
            Create Project
          </Button>
        </div>
      </div>

      {hasProjects ? (
        <>
          {/* Filters and View Toggle */}
          <div className="glass-premium p-4 rounded-xl space-y-4 fade-in-delay-1">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-white/50 backdrop-blur-xl border-white/30"
                />
              </div>

              {/* Sort */}
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
                <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
                  <SelectTrigger className="w-40 bg-white/50 backdrop-blur-xl border-white/30">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="glass-premium">
                    <SelectItem value="name">Name</SelectItem>
                    <SelectItem value="created_at">Created Date</SelectItem>
                    <SelectItem value="progress">Progress</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
                  <SelectTrigger className="w-32 bg-white/50 backdrop-blur-xl border-white/30">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="glass-premium">
                    <SelectItem value="asc">Ascending</SelectItem>
                    <SelectItem value="desc">Descending</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* View Toggle */}
              <div className="flex items-center gap-2 p-1 bg-white/30 rounded-lg">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  className={cn(viewMode === 'grid' && 'bg-white/60 shadow-md')}
                >
                  <Grid3x3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'table' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('table')}
                  className={cn(viewMode === 'table' && 'bg-white/60 shadow-md')}
                >
                  <TableIcon className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Projects Display */}
          {filteredProjects.length === 0 ? (
            <div className="glass-card p-12 text-center fade-in-delay-2">
              <p className="text-muted-foreground">No projects match your search.</p>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 fade-in-delay-2">
              {filteredProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onEdit={setEditingProject}
                  onDelete={handleDeleteSuccess}
                />
              ))}
            </div>
          ) : (
            <div className="fade-in-delay-2">
              <ProjectTable
                projects={filteredProjects}
                onEdit={setEditingProject}
                onDelete={handleDeleteSuccess}
              />
            </div>
          )}
        </>
      ) : (
        /* Empty State */
        <div className="glass-premium p-16 text-center space-y-8 shine fade-in-delay-1">
          <div className="flex justify-center">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-purple-600/20 rounded-full blur-3xl animate-pulse"></div>
              <div className="relative p-8 bg-gradient-to-br from-blue-500/10 to-purple-600/10 rounded-full backdrop-blur-xl">
                <FolderKanban className="h-24 w-24 text-blue-600" />
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              No Projects Yet
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
              Create your first project to start managing stories, tracking metrics, and optimizing your workflow with Lean Kanban.
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            size="lg"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-xl hover:shadow-2xl transition-all duration-500 hover:scale-105 text-lg px-8 py-6"
          >
            <Plus className="h-6 w-6 mr-2" />
            Create Your First Project
          </Button>
        </div>
      )}

      {/* Create/Edit Dialog */}
      <ProjectFormDialog
        open={showCreateDialog || !!editingProject}
        onClose={() => {
          setShowCreateDialog(false)
          setEditingProject(null)
        }}
        project={editingProject}
        onSuccess={editingProject ? handleEditSuccess : handleCreateSuccess}
      />
    </div>
  )
}
