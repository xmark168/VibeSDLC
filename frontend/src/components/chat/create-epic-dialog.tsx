import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Layers } from "lucide-react"

export interface NewEpicData {
  title: string
  description: string
  domain: string
}

interface CreateEpicDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateEpic: (epic: NewEpicData) => void
}

const DOMAIN_OPTIONS = [
  { value: "User Interface", label: "User Interface (UI)" },
  { value: "Backend", label: "Backend / API" },
  { value: "Database", label: "Database" },
  { value: "Authentication", label: "Authentication & Security" },
  { value: "Integration", label: "Integration / Third-party" },
  { value: "DevOps", label: "DevOps / Infrastructure" },
  { value: "Analytics", label: "Analytics & Reporting" },
  { value: "Payment", label: "Payment & Billing" },
  { value: "Notification", label: "Notification" },
  { value: "General", label: "General" },
]

export function CreateEpicDialog({ open, onOpenChange, onCreateEpic }: CreateEpicDialogProps) {
  const [formData, setFormData] = useState<NewEpicData>({
    title: "",
    description: "",
    domain: "General"
  })

  const handleSubmit = () => {
    if (!formData.title.trim()) {
      alert("Please enter Epic name")
      return
    }

    onCreateEpic(formData)
    handleReset()
    onOpenChange(false)
  }

  const handleReset = () => {
    setFormData({
      title: "",
      description: "",
      domain: "General"
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers className="w-5 h-5" />
            Create New Epic
          </DialogTitle>
          <DialogDescription>
            An Epic is a group of User Stories related to the same large feature
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="epic-title" className="text-sm font-semibold">
              Epic Name *
            </Label>
            <Input
              id="epic-title"
              placeholder="e.g., User Management, Payment System..."
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="h-10"
              autoFocus
            />
          </div>

          {/* Domain */}
          <div className="space-y-2">
            <Label htmlFor="epic-domain" className="text-sm font-semibold">
              Domain
            </Label>
            <Select
              value={formData.domain}
              onValueChange={(value) => setFormData(prev => ({ ...prev, domain: value }))}
            >
              <SelectTrigger id="epic-domain" className="h-10">
                <SelectValue placeholder="Select domain..." />
              </SelectTrigger>
              <SelectContent>
                {DOMAIN_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="epic-description" className="text-sm font-semibold">
              Description
            </Label>
            <Textarea
              id="epic-description"
              placeholder="Describe this Epic in detail..."
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="min-h-[80px] resize-none"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => {
              handleReset()
              onOpenChange(false)
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!formData.title.trim()}
          >
            Create Epic
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
