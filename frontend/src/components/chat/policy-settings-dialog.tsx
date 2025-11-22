import { useState, useEffect } from "react"
import { Settings, Plus, Trash2, CheckCircle2, AlertCircle, Save } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"

interface WorkflowPolicy {
  id?: string
  from_status: string
  to_status: string
  criteria: {
    assignee_required?: boolean
    story_points_estimated?: boolean
    no_blockers?: boolean
    acceptance_criteria_defined?: boolean
    reviewer_id?: boolean
  }
  is_active: boolean
}

interface PolicySettingsDialogProps {
  projectId?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const statusOptions = ["Todo", "InProgress", "Review", "Done"]

const criteriaOptions = [
  { key: "assignee_required", label: "Assignee Required", icon: "👤" },
  { key: "story_points_estimated", label: "Story Points Estimated", icon: "📊" },
  { key: "acceptance_criteria_defined", label: "Acceptance Criteria Defined", icon: "✓" },
  { key: "reviewer_id", label: "Reviewer Assigned", icon: "👁️" },
]

export function PolicySettingsDialog({
  projectId,
  open,
  onOpenChange,
}: PolicySettingsDialogProps) {
  const [policies, setPolicies] = useState<WorkflowPolicy[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (open && projectId) {
      loadPolicies()
    }
  }, [open, projectId])

  const loadPolicies = async () => {
    if (!projectId) return

    setLoading(true)
    setError(null)
    try {
      // TODO: Replace with actual API call
      // const response = await backlogItemsApi.getPolicies(projectId)
      // setPolicies(response.data)

      // Mock data for now
      setPolicies([
        {
          from_status: "Todo",
          to_status: "InProgress",
          criteria: {
            assignee_required: true,
            story_points_estimated: true,
          },
          is_active: true,
        },
        {
          from_status: "InProgress",
          to_status: "Review",
          criteria: {},
          is_active: true,
        },
      ])
    } catch (err) {
      setError("Failed to load policies")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const initializeDefaults = async () => {
    if (!projectId) return

    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      // TODO: Replace with actual API call
      // await backlogItemsApi.initializeDefaultPolicies(projectId)

      setSuccess("Default policies initialized successfully")
      await loadPolicies()
    } catch (err) {
      setError("Failed to initialize default policies")
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const updatePolicyCriteria = (index: number, criteriaKey: string, value: boolean) => {
    setPolicies((prev) =>
      prev.map((policy, i) =>
        i === index
          ? {
              ...policy,
              criteria: {
                ...policy.criteria,
                [criteriaKey]: value,
              },
            }
          : policy
      )
    )
  }

  const togglePolicyActive = (index: number) => {
    setPolicies((prev) =>
      prev.map((policy, i) =>
        i === index ? { ...policy, is_active: !policy.is_active } : policy
      )
    )
  }

  const saveChanges = async () => {
    if (!projectId) return

    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      // TODO: Replace with actual API calls
      // for (const policy of policies) {
      //   await backlogItemsApi.updatePolicy(projectId, policy)
      // }

      setSuccess("Policies saved successfully")
    } catch (err) {
      setError("Failed to save policies")
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "inprogress":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "review":
        return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
      case "done":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Workflow Policy Settings
          </DialogTitle>
          <DialogDescription>
            Configure Definition of Ready (DoR) and Definition of Done (DoD) criteria for status transitions.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="border-green-500/50 bg-green-50 dark:bg-green-950/20">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-600 dark:text-green-400">
              {success}
            </AlertDescription>
          </Alert>
        )}

        <Separator />

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-sm text-muted-foreground">Loading policies...</div>
          </div>
        ) : policies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <AlertCircle className="w-12 h-12 text-muted-foreground" />
            <div className="text-sm text-muted-foreground text-center">
              No workflow policies configured yet.
            </div>
            <Button onClick={initializeDefaults} disabled={saving}>
              <Plus className="w-4 h-4 mr-2" />
              Initialize Default Policies
            </Button>
          </div>
        ) : (
          <ScrollArea className="max-h-[500px] pr-4">
            <div className="space-y-6">
              {policies.map((policy, index) => (
                <div
                  key={index}
                  className={`rounded-lg border p-4 space-y-4 ${
                    policy.is_active
                      ? "border-border bg-card"
                      : "border-muted bg-muted/30 opacity-60"
                  }`}
                >
                  {/* Policy Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className={getStatusBadgeColor(policy.from_status)}>
                        {policy.from_status}
                      </Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge variant="outline" className={getStatusBadgeColor(policy.to_status)}>
                        {policy.to_status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`active-${index}`} className="text-sm cursor-pointer">
                        {policy.is_active ? "Active" : "Inactive"}
                      </Label>
                      <Checkbox
                        id={`active-${index}`}
                        checked={policy.is_active}
                        onCheckedChange={() => togglePolicyActive(index)}
                      />
                    </div>
                  </div>

                  <Separator />

                  {/* Criteria */}
                  <div className="space-y-3">
                    <div className="text-sm font-semibold">Required Criteria:</div>
                    <div className="grid grid-cols-2 gap-3">
                      {criteriaOptions.map((criteria) => (
                        <div
                          key={criteria.key}
                          className="flex items-center space-x-2 p-2 rounded-md hover:bg-muted/50"
                        >
                          <Checkbox
                            id={`${index}-${criteria.key}`}
                            checked={!!policy.criteria[criteria.key as keyof typeof policy.criteria]}
                            onCheckedChange={(checked) =>
                              updatePolicyCriteria(index, criteria.key, !!checked)
                            }
                            disabled={!policy.is_active}
                          />
                          <label
                            htmlFor={`${index}-${criteria.key}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex items-center gap-2"
                          >
                            <span>{criteria.icon}</span>
                            <span>{criteria.label}</span>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}

        <Separator />

        {/* Actions */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <div className="flex gap-2">
            {policies.length > 0 && (
              <Button onClick={initializeDefaults} variant="outline" disabled={saving}>
                <Plus className="w-4 h-4 mr-2" />
                Add More Policies
              </Button>
            )}
            <Button onClick={saveChanges} disabled={saving || policies.length === 0}>
              <Save className="w-4 h-4 mr-2" />
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
