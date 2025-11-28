import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, ExternalLink } from "lucide-react"

interface PrdCreatedCardProps {
  title: string
  filePath: string
  onView?: () => void
}

export function PrdCreatedCard({ title, filePath, onView }: PrdCreatedCardProps) {
  return (
    <Card className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/20">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-green-500/20">
          <FileText className="w-5 h-5 text-green-600" />
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="text-sm">
            {title}
          </h4>
        </div>

        <Button 
          size="sm" 
          variant="outline"
          className="gap-1.5 border-green-500/30 hover:bg-green-500/10"
          onClick={onView}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View
        </Button>
      </div>
    </Card>
  )
}
