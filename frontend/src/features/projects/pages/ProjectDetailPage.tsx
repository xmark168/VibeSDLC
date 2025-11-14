import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, MessageSquare, LayoutGrid, Loader2, Plus, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { ChatInterface } from '../components/chat/ChatInterface'
import { KanbanBoard } from '../components/kanban/KanbanBoard'
import { StoryDetailDialog } from '../components/kanban/StoryDetailDialog'
import { StoryFormDialog } from '../components/kanban/StoryFormDialog'
import { EpicListDialog } from '../components/epic/EpicListDialog'
import { projectsAPI } from '../api/projects'
import { getIconByName } from '@/shared/components/IconPicker'
import type { Project } from '../types/project'
import type { BoardView, Story } from '../types/board'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

export const ProjectDetailPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [boardData, setBoardData] = useState<BoardView | null>(null)
  const [isLoadingProject, setIsLoadingProject] = useState(true)
  const [isLoadingBoard, setIsLoadingBoard] = useState(true)

  // Dialog states
  const [selectedStory, setSelectedStory] = useState<Story | null>(null)
  const [isStoryDetailOpen, setIsStoryDetailOpen] = useState(false)
  const [isStoryFormOpen, setIsStoryFormOpen] = useState(false)
  const [isEpicListOpen, setIsEpicListOpen] = useState(false)

  // Mobile tab state
  const [mobileTab, setMobileTab] = useState<'chat' | 'kanban'>('kanban')

  useEffect(() => {
    if (!id) return

    const fetchProject = async () => {
      try {
        setIsLoadingProject(true)
        const data = await projectsAPI.getProject(parseInt(id))
        setProject(data)
      } catch (error) {
        console.error('Failed to fetch project:', error)
      } finally {
        setIsLoadingProject(false)
      }
    }

    const fetchBoard = async () => {
      try {
        setIsLoadingBoard(true)
        const data = await projectsAPI.getProjectBoard(parseInt(id))
        setBoardData(data)
      } catch (error) {
        console.error('Failed to fetch board:', error)
      } finally {
        setIsLoadingBoard(false)
      }
    }

    fetchProject()
    fetchBoard()
  }, [id])

  const handleStoryClick = (story: Story) => {
    setSelectedStory(story)
    setIsStoryDetailOpen(true)
  }

  const handleAddStory = () => {
    setIsStoryFormOpen(true)
  }

  const handleMoveStory = async (storyId: number, fromStatus: string, toStatus: string) => {
    console.log('handleMoveStory called:', { storyId, fromStatus, toStatus, toStatusType: typeof toStatus })

    try {
      // Update story status via API
      await projectsAPI.updateStoryStatus(storyId, toStatus)

      // Refresh board data to reflect the change
      if (!id) return
      const data = await projectsAPI.getProjectBoard(parseInt(id))
      setBoardData(data)

      // Show success message
      toast.success(`Story moved to ${toStatus.replace('_', ' ')}`)
    } catch (error: any) {
      console.error('Failed to move story:', error)
      console.error('Error response:', error.response?.data)

      // Extract error message
      let errorMessage = 'Failed to move story'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        // Handle validation error array format
        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg).join(', ')
        } else if (typeof detail === 'string') {
          errorMessage = detail
        }
      } else if (error.message) {
        errorMessage = error.message
      }

      toast.error(errorMessage)

      // Refresh board to revert optimistic update if any
      if (!id) return
      try {
        const data = await projectsAPI.getProjectBoard(parseInt(id))
        setBoardData(data)
      } catch (refreshError) {
        console.error('Failed to refresh board:', refreshError)
      }
    }
  }

  const handleStoryCreated = async () => {
    // Refresh board data after story is created
    if (!id) return
    try {
      const data = await projectsAPI.getProjectBoard(parseInt(id))
      setBoardData(data)
    } catch (error) {
      console.error('Failed to refresh board:', error)
    }
  }

  if (isLoadingProject) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto" />
          <p className="text-sm text-gray-600 font-medium">Loading project...</p>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center space-y-3">
          <p className="text-lg font-semibold text-gray-700">Project not found</p>
          <Button onClick={() => navigate('/projects')}>Go back to projects</Button>
        </div>
      </div>
    )
  }

  const ProjectIcon = getIconByName(project.icon)

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b-2 border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/projects')} className="flex-shrink-0">
            <ArrowLeft className="h-5 w-5" />
          </Button>

          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: project.color || '#3b82f6' }}
          >
            <ProjectIcon className="h-6 w-6 text-white" />
          </div>

          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">{project.name}</h1>
            <p className="text-sm text-gray-600 truncate">{project.code}</p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button onClick={() => setIsEpicListOpen(true)} variant="outline">
              <Layers className="h-4 w-4 mr-2" />
              Manage Epics
            </Button>
            <Button onClick={handleAddStory} className="bg-blue-500 hover:bg-blue-600">
              <Plus className="h-4 w-4 mr-2" />
              Add Story
            </Button>
          </div>
        </div>
      </header>

      {/* Tabs Layout for All Screen Sizes */}
      <div className="flex-1 flex flex-col p-6 overflow-hidden">
        <Tabs value={mobileTab} onValueChange={(v) => setMobileTab(v as 'chat' | 'kanban')} className="flex flex-col h-full">
          <TabsList className="grid w-full grid-cols-2 bg-white border-2 border-gray-200 p-1 h-12 rounded-xl mb-4">
            <TabsTrigger
              value="chat"
              className={cn(
                'flex items-center gap-2 h-9 rounded-lg transition-all',
                mobileTab === 'chat' && 'bg-blue-500 text-white shadow-md'
              )}
            >
              <MessageSquare className="h-4 w-4" />
              <span>Chat</span>
            </TabsTrigger>
            <TabsTrigger
              value="kanban"
              className={cn(
                'flex items-center gap-2 h-9 rounded-lg transition-all',
                mobileTab === 'kanban' && 'bg-blue-500 text-white shadow-md'
              )}
            >
              <LayoutGrid className="h-4 w-4" />
              <span>Board</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="flex-1 mt-0 overflow-hidden">
            <ChatInterface />
          </TabsContent>

          <TabsContent value="kanban" className="flex-1 mt-0 overflow-hidden">
            <KanbanBoard
              boardData={boardData}
              isLoading={isLoadingBoard}
              onStoryClick={handleStoryClick}
              onMoveStory={handleMoveStory}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialogs */}
      <StoryDetailDialog
        story={selectedStory}
        open={isStoryDetailOpen}
        onOpenChange={setIsStoryDetailOpen}
      />
      <StoryFormDialog
        open={isStoryFormOpen}
        onOpenChange={setIsStoryFormOpen}
        onSuccess={handleStoryCreated}
      />
      <EpicListDialog
        open={isEpicListOpen}
        onOpenChange={setIsEpicListOpen}
        projectId={parseInt(id || '0')}
      />
    </div>
  )
}
