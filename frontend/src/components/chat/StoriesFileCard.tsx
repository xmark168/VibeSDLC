import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ListTodo, ExternalLink } from "lucide-react"

interface StoriesFileCardProps {
  count: number
  filePath: string
  onView?: () => void
}

export function StoriesFileCard({ count, filePath, onView }: StoriesFileCardProps) {
  return (
    <Card className="p-4 bg-gradient-to-r from-purple-500/10 to-violet-500/10 border-purple-500/20">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-purple-500/20">
          <ListTodo className="w-5 h-5 text-purple-600" />
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-purple-700 dark:text-purple-400">
            ✅ User Stories đã được tạo
          </h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            {count} stories
          </p>
        </div>

        <Button 
          size="sm" 
          variant="outline"
          className="gap-1.5 border-purple-500/30 hover:bg-purple-500/10"
          onClick={onView}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View
        </Button>
      </div>
    </Card>
  )
}
