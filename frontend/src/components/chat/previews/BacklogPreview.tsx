import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

interface EpicData {
  id: string
  name: string
  description: string
  domain: string
}

interface StoryData {
  epic_id: string
  title: string
  description: string
  acceptance_criteria: string[]
  story_points: number
  priority: string
}

interface BacklogPreviewProps {
  backlog: {
    epics: EpicData[]
    stories: StoryData[]
  }
}

export function BacklogPreview({ backlog }: BacklogPreviewProps) {
  const [expandedEpics, setExpandedEpics] = useState<Set<string>>(new Set())

  if (!backlog || !backlog.epics || !backlog.stories) return null

  const { epics, stories } = backlog

  const toggleExpand = (epicId: string) => {
    setExpandedEpics(prev => {
      const next = new Set(prev)
      if (next.has(epicId)) {
        next.delete(epicId)
      } else {
        next.add(epicId)
      }
      return next
    })
  }

  const getStoriesForEpic = (epicId: string) => {
    return stories.filter(story => story.epic_id === epicId)
  }

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300'
      case 'low':
        return 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
    }
  }

  // Calculate totals
  const totalStoryPoints = stories.reduce((sum, story) => sum + (story.story_points || 0), 0)

  return (
    <div className="space-y-4 max-h-[500px] overflow-y-auto">
      {/* Summary */}
      <div className="p-4 bg-muted rounded-lg">
        <h4 className="text-sm font-semibold text-foreground mb-2">
          Tóm tắt Backlog
        </h4>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-muted-foreground">Epics:</span>
            <span className="ml-2 font-medium">{epics.length}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Stories:</span>
            <span className="ml-2 font-medium">{stories.length}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Story Points:</span>
            <span className="ml-2 font-medium">{totalStoryPoints}</span>
          </div>
        </div>
      </div>

      {/* Epics and Stories */}
      <div className="space-y-3">
        {epics.map((epic) => {
          const epicStories = getStoriesForEpic(epic.id)
          const isExpanded = expandedEpics.has(epic.id)

          return (
            <div key={epic.id} className="border rounded-lg overflow-hidden">
              {/* Epic Header */}
              <div
                className="p-3 bg-purple-50 dark:bg-purple-950 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900 transition-colors"
                onClick={() => toggleExpand(epic.id)}
              >
                <div className="flex items-start gap-2">
                  <button className="mt-0.5">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-purple-600" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-purple-600" />
                    )}
                  </button>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 text-xs">
                        Epic
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {epic.domain}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {epicStories.length} stories
                      </span>
                    </div>
                    <h5 className="text-sm font-medium text-foreground">
                      {epic.name}
                    </h5>
                    <p className="text-xs text-muted-foreground mt-1">
                      {epic.description}
                    </p>
                  </div>
                </div>
              </div>

              {/* Stories */}
              {isExpanded && epicStories.length > 0 && (
                <div className="border-t">
                  {epicStories.map((story, idx) => (
                    <Card key={idx} className="m-2 border-l-4 border-l-blue-500">
                      <CardContent className="p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 text-xs">
                            Story
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {story.story_points} SP
                          </Badge>
                          <Badge className={`text-xs ${getPriorityColor(story.priority)}`}>
                            {story.priority}
                          </Badge>
                        </div>
                        <h6 className="text-sm font-medium text-foreground mb-1">
                          {story.title}
                        </h6>
                        <p className="text-xs text-muted-foreground mb-2">
                          {story.description}
                        </p>
                        {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-foreground mb-1">
                              Acceptance Criteria:
                            </p>
                            <ul className="list-disc list-inside text-xs text-muted-foreground space-y-0.5">
                              {story.acceptance_criteria.map((criteria, i) => (
                                <li key={i}>{criteria}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
