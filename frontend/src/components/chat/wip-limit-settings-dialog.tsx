import { Settings, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useWIPLimits, useUpdateWIPLimit } from "@/queries/backlog-items"
import { useState, useEffect } from "react"

interface WIPLimitSettingsDialogProps {
  projectId: string | undefined
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ColumnConfig {
  name: string
  displayName: string
  description: string
  defaultLimit: number
}

const COLUMNS: ColumnConfig[] = [
  {
    name: "Todo",
    displayName: "To Do",
    description: "Items ready to be started",
    defaultLimit: 10,
  },
  {
    name: "InProgress",
    displayName: "In Progress",
    description: "Items currently being worked on",
    defaultLimit: 3,
  },
  {
    name: "Review",
    displayName: "Review",
    description: "Items awaiting review/testing",
    defaultLimit: 2,
  },
  {
    name: "Done",
    displayName: "Done",
    description: "Completed items",
    defaultLimit: 999,
  },
]

export function WIPLimitSettingsDialog({ projectId, open, onOpenChange }: WIPLimitSettingsDialogProps) {
  const { data: wipLimits, isLoading } = useWIPLimits(projectId)
  const updateWIPLimit = useUpdateWIPLimit(projectId || "")

  const [localSettings, setLocalSettings] = useState<Record<string, { limit: number; type: 'hard' | 'soft' }>>({})
  const [hasChanges, setHasChanges] = useState(false)

  // Initialize local settings when WIP limits are loaded
  useEffect(() => {
    if (wipLimits && wipLimits.data) {
      const settings: Record<string, { limit: number; type: 'hard' | 'soft' }> = {}

      COLUMNS.forEach((col) => {
        const wipLimit = wipLimits.data.find((w) => w.column_name === col.name)
        settings[col.name] = {
          limit: wipLimit?.wip_limit || col.defaultLimit,
          type: wipLimit?.limit_type || 'hard',
        }
      })

      setLocalSettings(settings)
      setHasChanges(false)
    }
  }, [wipLimits])

  const handleLimitChange = (columnName: string, value: string) => {
    const numValue = parseInt(value, 10)
    if (!isNaN(numValue) && numValue > 0) {
      setLocalSettings((prev) => ({
        ...prev,
        [columnName]: { ...prev[columnName], limit: numValue },
      }))
      setHasChanges(true)
    }
  }

  const handleTypeChange = (columnName: string, type: 'hard' | 'soft') => {
    setLocalSettings((prev) => ({
      ...prev,
      [columnName]: { ...prev[columnName], type },
    }))
    setHasChanges(true)
  }

  const handleSave = async () => {
    if (!projectId) return

    try {
      // Update each column's WIP limit
      const updates = COLUMNS.map((col) =>
        updateWIPLimit.mutateAsync({
          columnName: col.name,
          params: {
            wip_limit: localSettings[col.name]?.limit || col.defaultLimit,
            limit_type: localSettings[col.name]?.type || 'hard',
          },
        })
      )

      await Promise.all(updates)
      setHasChanges(false)
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to update WIP limits:", error)
    }
  }

  const handleReset = () => {
    if (wipLimits && wipLimits.data) {
      const settings: Record<string, { limit: number; type: 'hard' | 'soft' }> = {}
      COLUMNS.forEach((col) => {
        const wipLimit = wipLimits.data.find((w) => w.column_name === col.name)
        settings[col.name] = {
          limit: wipLimit?.wip_limit || col.defaultLimit,
          type: wipLimit?.limit_type || 'hard',
        }
      })
      setLocalSettings(settings)
      setHasChanges(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            WIP Limit Settings
          </DialogTitle>
          <DialogDescription>
            Configure Work In Progress limits for each column. Limits help prevent overload and maintain smooth flow.
          </DialogDescription>
        </DialogHeader>

        <Separator />

        {isLoading ? (
          <div className="py-8 text-center text-sm text-muted-foreground">Loading...</div>
        ) : (
          <div className="space-y-4">
            {/* Info Alert */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Hard limits</strong> block moving cards when the limit is reached.
                <br />
                <strong>Soft limits</strong> show a warning but allow the move with confirmation.
              </AlertDescription>
            </Alert>

            {/* Column Settings */}
            {COLUMNS.map((col) => (
              <div key={col.name} className="border rounded-lg p-4 space-y-3">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">{col.displayName}</h4>
                  <p className="text-xs text-muted-foreground">{col.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`${col.name}-limit`} className="text-xs">
                      WIP Limit
                    </Label>
                    <Input
                      id={`${col.name}-limit`}
                      type="number"
                      min="1"
                      value={localSettings[col.name]?.limit || col.defaultLimit}
                      onChange={(e) => handleLimitChange(col.name, e.target.value)}
                      className="h-9"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`${col.name}-type`} className="text-xs">
                      Enforcement Type
                    </Label>
                    <Select
                      value={localSettings[col.name]?.type || 'hard'}
                      onValueChange={(value: 'hard' | 'soft') => handleTypeChange(col.name, value)}
                    >
                      <SelectTrigger id={`${col.name}-type`} className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="hard">Hard (Block)</SelectItem>
                        <SelectItem value="soft">Soft (Warn)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <Separator />

        {/* Actions */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!hasChanges || updateWIPLimit.isPending}
            className="h-9"
          >
            Reset
          </Button>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="h-9"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={!hasChanges || updateWIPLimit.isPending}
              className="h-9"
            >
              {updateWIPLimit.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
