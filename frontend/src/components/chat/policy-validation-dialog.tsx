import { AlertCircle, XCircle, CheckCircle2, ArrowRight } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"

export interface PolicyViolation {
  error: string
  message: string
  violations: string[]
  policy: {
    from: string
    to: string
  }
}

interface PolicyValidationDialogProps {
  violation: PolicyViolation | null
  cardTitle?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PolicyValidationDialog({
  violation,
  cardTitle,
  open,
  onOpenChange,
}: PolicyValidationDialogProps) {
  if (!violation) return null

  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "inprogress":
      case "in_progress":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "review":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
      case "done":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  const formatStatusName = (status: string) => {
    return status
      .replace(/_/g, " ")
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ")
  }

  const getViolationIcon = (violation: string) => {
    if (violation.toLowerCase().includes("assignee")) {
      return "👤"
    } else if (violation.toLowerCase().includes("blocker")) {
      return "🚧"
    } else if (violation.toLowerCase().includes("acceptance criteria")) {
      return "✓"
    } else if (violation.toLowerCase().includes("story point")) {
      return "📊"
    } else if (violation.toLowerCase().includes("description")) {
      return "📝"
    }
    return "•"
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <XCircle className="w-5 h-5" />
            Workflow Policy Violation
          </DialogTitle>
          <DialogDescription>
            This card cannot be moved because it doesn't meet the required criteria.
          </DialogDescription>
        </DialogHeader>

        <Separator />

        {/* Card Info */}
        {cardTitle && (
          <div className="rounded-lg bg-muted/50 p-3">
            <div className="text-xs text-muted-foreground mb-1">Moving card:</div>
            <div className="text-sm font-medium">{cardTitle}</div>
          </div>
        )}

        {/* Status Transition */}
        <div className="flex items-center justify-center gap-3">
          <Badge variant="outline" className={getStatusBadgeColor(violation.policy.from)}>
            {formatStatusName(violation.policy.from)}
          </Badge>
          <ArrowRight className="w-4 h-4 text-muted-foreground" />
          <Badge variant="outline" className={getStatusBadgeColor(violation.policy.to)}>
            {formatStatusName(violation.policy.to)}
          </Badge>
        </div>

        {/* Main Alert */}
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">
            {violation.message}
          </AlertDescription>
        </Alert>

        {/* Violations List */}
        <div className="space-y-3">
          <div className="text-sm font-semibold text-foreground">
            Required criteria not met:
          </div>
          <div className="space-y-2">
            {violation.violations.map((v, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/20"
              >
                <span className="text-lg mt-0.5">{getViolationIcon(v)}</span>
                <div className="flex-1">
                  <p className="text-sm text-foreground">{v}</p>
                </div>
                <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5" />
              </div>
            ))}
          </div>
        </div>

        {/* Instructions */}
        <div className="rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-sm font-medium">What to do:</span>
          </div>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 ml-6 list-disc">
            <li>Open the card details by clicking on it</li>
            <li>Address each violation listed above</li>
            <li>Try moving the card again after fixing the issues</li>
          </ul>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex justify-end">
          <Button onClick={() => onOpenChange(false)}>
            Got it
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
