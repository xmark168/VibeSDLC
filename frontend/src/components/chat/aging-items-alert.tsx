import { useState, useEffect } from "react"
import { Clock, AlertTriangle, ChevronDown, ChevronUp, X } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ScrollArea } from "@/components/ui/scroll-area"

interface AgingItem {
  id: string
  title: string
  status: string
  age_hours: number
}

interface AgingItemsAlertProps {
  projectId?: string
  agingItems?: AgingItem[]
  onCardClick?: (itemId: string) => void
}

export function AgingItemsAlert({
  projectId,
  agingItems = [],
  onCardClick,
}: AgingItemsAlertProps) {
  const [isOpen, setIsOpen] = useState(true)
  const [isDismissed, setIsDismissed] = useState(false)

  const formatAge = (hours: number) => {
    const days = Math.floor(hours / 24)
    const remainingHours = Math.floor(hours % 24)

    if (days > 0) {
      return `${days}d ${remainingHours}h`
    }
    return `${remainingHours}h`
  }

  const getAgeSeverity = (hours: number) => {
    if (hours >= 168) return { color: "destructive", label: "Critical", icon: "🔴" } // 7+ days
    if (hours >= 120) return { color: "warning", label: "High", icon: "🟠" } // 5-7 days
    if (hours >= 72) return { color: "caution", label: "Medium", icon: "🟡" } // 3-5 days
    return { color: "info", label: "Low", icon: "🔵" }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "inprogress":
      case "in_progress":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "review":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Sort by age (oldest first)
  const sortedItems = [...agingItems].sort((a, b) => b.age_hours - a.age_hours)

  // Don't show if dismissed or no aging items
  if (isDismissed || agingItems.length === 0) {
    return null
  }

  const criticalCount = agingItems.filter(item => item.age_hours >= 168).length
  const highCount = agingItems.filter(item => item.age_hours >= 120 && item.age_hours < 168).length

  return (
    <Alert className="mb-4 border-orange-500/50 bg-orange-50 dark:bg-orange-950/20">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
            <div className="flex-1">
              <AlertDescription className="text-orange-900 dark:text-orange-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-semibold flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    {agingItems.length} Aging Item{agingItems.length !== 1 ? "s" : ""} Detected
                  </div>
                  <div className="flex items-center gap-2">
                    {criticalCount > 0 && (
                      <Badge variant="destructive" className="text-xs">
                        {criticalCount} Critical
                      </Badge>
                    )}
                    {highCount > 0 && (
                      <Badge className="text-xs bg-orange-500">
                        {highCount} High
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="text-sm text-orange-700 dark:text-orange-300">
                  These items have been in their current status for more than 3 days.
                </div>
              </AlertDescription>

              <CollapsibleContent>
                <ScrollArea className="max-h-60 mt-3">
                  <div className="space-y-2">
                    {sortedItems.map((item) => {
                      const severity = getAgeSeverity(item.age_hours)
                      return (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-2 rounded-md bg-white dark:bg-gray-900 border border-orange-200 dark:border-orange-900 hover:bg-orange-50 dark:hover:bg-orange-950/30 cursor-pointer transition-colors"
                          onClick={() => onCardClick?.(item.id)}
                        >
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className="text-lg">{severity.icon}</span>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium truncate text-foreground">
                                {item.title}
                              </div>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge
                                  variant="outline"
                                  className={`${getStatusBadgeColor(item.status)} text-xs`}
                                >
                                  {item.status}
                                </Badge>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 ml-2">
                            <Badge
                              variant="outline"
                              className={`text-xs ${
                                item.age_hours >= 168
                                  ? "bg-red-100 text-red-700 border-red-300"
                                  : item.age_hours >= 120
                                  ? "bg-orange-100 text-orange-700 border-orange-300"
                                  : "bg-yellow-100 text-yellow-700 border-yellow-300"
                              }`}
                            >
                              {formatAge(item.age_hours)}
                            </Badge>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </ScrollArea>
              </CollapsibleContent>
            </div>
          </div>

          <div className="flex items-center gap-1 ml-2">
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-orange-600 hover:text-orange-700 hover:bg-orange-100 dark:hover:bg-orange-900"
              >
                {isOpen ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-orange-600 hover:text-orange-700 hover:bg-orange-100 dark:hover:bg-orange-900"
              onClick={() => setIsDismissed(true)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Collapsible>
    </Alert>
  )
}
