import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  RefreshCcw,
  Trash2,
  X,
} from "lucide-react"
import { useState } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { toast } from "@/lib/toast"
import {
  useBulkRestart,
  useBulkSetIdle,
  useBulkTerminate,
} from "@/queries/agents"

interface BulkActionsToolbarProps {
  selectedIds: string[]
  onClearSelection: () => void
  onActionComplete?: () => void
}

type BulkAction = "terminate" | "set-idle" | "restart" | null

export function BulkActionsToolbar({
  selectedIds,
  onClearSelection,
  onActionComplete,
}: BulkActionsToolbarProps) {
  const [confirmAction, setConfirmAction] = useState<BulkAction>(null)

  const bulkTerminate = useBulkTerminate()
  const bulkSetIdle = useBulkSetIdle()
  const bulkRestart = useBulkRestart()

  const isLoading =
    bulkTerminate.isPending || bulkSetIdle.isPending || bulkRestart.isPending

  const handleAction = async (action: BulkAction) => {
    if (!action) return

    try {
      let result
      switch (action) {
        case "terminate":
          result = await bulkTerminate.mutateAsync({
            agentIds: selectedIds,
            graceful: true,
          })
          toast.success(
            `${result.message} (${result.success_count} succeeded, ${result.failed_count} failed)`,
          )
          break
        case "set-idle":
          result = await bulkSetIdle.mutateAsync(selectedIds)
          toast.success(
            `${result.message} (${result.success_count} succeeded, ${result.failed_count} failed)`,
          )
          break
        case "restart":
          result = await bulkRestart.mutateAsync(selectedIds)
          toast.success(
            `${result.message} (${result.success_count} succeeded, ${result.failed_count} failed)`,
          )
          break
      }

      onClearSelection()
      onActionComplete?.()
    } catch (error: any) {
      toast.error(`Bulk ${action} failed: ${error.message}`)
    }

    setConfirmAction(null)
  }

  if (selectedIds.length === 0) return null

  return (
    <>
      <div className="flex items-center gap-2 p-3 bg-muted/50 border rounded-lg mb-4">
        <Badge variant="secondary" className="mr-2">
          {selectedIds.length} selected
        </Badge>

        <div className="flex items-center gap-2 flex-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setConfirmAction("set-idle")}
            disabled={isLoading}
          >
            {bulkSetIdle.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Clock className="w-4 h-4 mr-2" />
            )}
            Set Idle
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setConfirmAction("restart")}
            disabled={isLoading}
          >
            {bulkRestart.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCcw className="w-4 h-4 mr-2" />
            )}
            Restart
          </Button>

          <Button
            variant="destructive"
            size="sm"
            onClick={() => setConfirmAction("terminate")}
            disabled={isLoading}
          >
            {bulkTerminate.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4 mr-2" />
            )}
            Terminate
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onClearSelection}
          disabled={isLoading}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog
        open={!!confirmAction}
        onOpenChange={() => setConfirmAction(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              {confirmAction === "terminate" ? (
                <AlertTriangle className="w-5 h-5 text-destructive" />
              ) : (
                <CheckCircle className="w-5 h-5 text-primary" />
              )}
              Confirm Bulk{" "}
              {confirmAction
                ?.replace("-", " ")
                .replace(/^\w/, (c) => c.toUpperCase())}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction === "terminate" && (
                <>
                  Are you sure you want to terminate{" "}
                  <strong>{selectedIds.length}</strong> agents? This action
                  cannot be undone.
                </>
              )}
              {confirmAction === "set-idle" && (
                <>
                  Set <strong>{selectedIds.length}</strong> agents to idle
                  state? They will stop current work and become available.
                </>
              )}
              {confirmAction === "restart" && (
                <>
                  Restart <strong>{selectedIds.length}</strong> agents? Each
                  agent will be terminated and respawned.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleAction(confirmAction)}
              disabled={isLoading}
              className={
                confirmAction === "terminate"
                  ? "bg-destructive hover:bg-destructive/90"
                  : ""
              }
            >
              {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
