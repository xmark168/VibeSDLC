import { useNavigate } from "@tanstack/react-router"
import { CheckCircle2, ExternalLink, ListTodo } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface StoriesCreatedCardProps {
  stories: {
    count: number
    story_ids: string[]
    prd_artifact_id?: string
  }
  projectId: string
}

export function StoriesCreatedCard({
  stories,
  projectId,
}: StoriesCreatedCardProps) {
  const navigate = useNavigate()

  const handleViewKanban = () => {
    navigate({ to: `/projects/${projectId}/kanban` })
  }

  return (
    <Card className="my-2 border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-950/20">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900">
            <ListTodo className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-100">
                User Stories Created!
              </h4>
            </div>

            <p className="text-sm text-purple-800 dark:text-purple-200 mb-2">
              {stories.count} user {stories.count === 1 ? "story" : "stories"}{" "}
              đã được tạo và thêm vào backlog
            </p>

            <div className="flex items-center gap-2 mb-3">
              <div className="flex -space-x-1">
                {stories.story_ids.slice(0, 5).map((id, idx) => (
                  <div
                    key={id}
                    className="w-6 h-6 rounded-full bg-purple-200 dark:bg-purple-800 border-2 border-white dark:border-gray-900 flex items-center justify-center text-xs font-medium text-purple-700 dark:text-purple-300"
                    title={`Story ${id.substring(0, 8)}`}
                  >
                    {idx + 1}
                  </div>
                ))}
                {stories.story_ids.length > 5 && (
                  <div className="w-6 h-6 rounded-full bg-purple-300 dark:bg-purple-700 border-2 border-white dark:border-gray-900 flex items-center justify-center text-xs font-medium text-purple-800 dark:text-purple-200">
                    +{stories.story_ids.length - 5}
                  </div>
                )}
              </div>
              <span className="text-xs text-purple-600 dark:text-purple-400">
                Status: TODO
              </span>
            </div>

            <p className="text-xs text-purple-600 dark:text-purple-400">
              Team Leader sẽ assign stories cho developers
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2">
            <Button
              size="sm"
              variant="default"
              className="bg-purple-600 hover:bg-purple-700 text-white"
              onClick={handleViewKanban}
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              View Kanban
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
