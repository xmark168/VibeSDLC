import { Code, Database, FileCode, FileText, FlaskConical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface ArtifactCardProps {
  artifact: {
    artifact_id: string
    artifact_type: string
    title: string
    description?: string
    version: number
    status: string
    agent_name: string
  }
  onClick: () => void
}

const ARTIFACT_ICONS: Record<string, any> = {
  prd: FileText,
  analysis: FileText,
  architecture: Database,
  code: Code,
  test_plan: FlaskConical,
  api_spec: FileCode,
  database_schema: Database,
  user_stories: FileText,
  review: FileText,
}

export function ArtifactCard({ artifact, onClick }: ArtifactCardProps) {
  const Icon = ARTIFACT_ICONS[artifact.artifact_type] || FileText

  return (
    <Card
      className="my-2 border-blue-200 dark:border-blue-800 cursor-pointer hover:bg-accent/50 transition-colors"
      onClick={onClick}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900">
            <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-semibold truncate">
                {artifact.title}
              </h4>
              <span className="text-xs px-1.5 py-0.5 rounded bg-muted">
                v{artifact.version}
              </span>
            </div>

            {artifact.description && (
              <p className="text-xs text-muted-foreground line-clamp-1">
                {artifact.description}
              </p>
            )}

            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <span>by {artifact.agent_name}</span>
              <span>•</span>
              <span
                className={`px-2 py-0.5 rounded ${
                  artifact.status === "approved"
                    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                    : artifact.status === "draft"
                      ? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                      : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                }`}
              >
                {artifact.status}
              </span>
            </div>
          </div>

          <Button size="sm" variant="ghost">
            View →
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
