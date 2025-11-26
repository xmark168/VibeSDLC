import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Zap, Flag, X } from "lucide-react"
import type { StoryFormData } from "@/types"

export type { StoryFormData }

interface CreateStoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateStory: (story: StoryFormData) => void
}

export function CreateStoryDialog({ open, onOpenChange, onCreateStory }: CreateStoryDialogProps) {
  const [formData, setFormData] = useState<StoryFormData>({
    title: "",
    description: "",
    type: "UserStory",
    story_point: undefined,
    priority: "Medium",
    acceptance_criteria: []
  })

  const [currentCriteria, setCurrentCriteria] = useState("")

  const handleSubmit = () => {
    if (!formData.title.trim()) {
      alert("Please enter a story title")
      return
    }

    onCreateStory(formData)
    handleReset()
    onOpenChange(false)
  }

  const handleReset = () => {
    setFormData({
      title: "",
      description: "",
      type: "UserStory",
      story_point: undefined,
      priority: "Medium",
      acceptance_criteria: []
    })
    setCurrentCriteria("")
  }

  const handleAddCriteria = () => {
    if (currentCriteria.trim()) {
      setFormData(prev => ({
        ...prev,
        acceptance_criteria: [...prev.acceptance_criteria, currentCriteria.trim()]
      }))
      setCurrentCriteria("")
    }
  }

  const handleRemoveCriteria = (index: number) => {
    setFormData(prev => ({
      ...prev,
      acceptance_criteria: prev.acceptance_criteria.filter((_, i) => i !== index)
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">Create New Story</DialogTitle>
          <DialogDescription>
            Fill in the details below to create a new story on the Kanban board
          </DialogDescription>
        </DialogHeader>

        <Separator />

        <div className="space-y-4">
          {/* Story Type */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Story Type *</Label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, type: "UserStory" }))}
                className={`flex-1 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                  formData.type === "UserStory"
                    ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 border-2 border-blue-200 dark:border-blue-800"
                    : "bg-muted/30 text-muted-foreground hover:bg-muted/50 border-2 border-transparent"
                }`}
              >
                User Story
              </button>
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, type: "EnablerStory" }))}
                className={`flex-1 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                  formData.type === "EnablerStory"
                    ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-2 border-emerald-200 dark:border-emerald-800"
                    : "bg-muted/30 text-muted-foreground hover:bg-muted/50 border-2 border-transparent"
                }`}
              >
                Enabler Story
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              {formData.type === "UserStory"
                ? "User-facing features that deliver direct value to end users"
                : "Infrastructure, technical foundations, and architectural work"}
            </p>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title" className="text-sm font-semibold">
              Story Title *
            </Label>
            <Input
              id="title"
              placeholder="As a [role], I want [feature] so that [benefit]"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="h-10"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-semibold">
              Description
            </Label>
            <Textarea
              id="description"
              placeholder="Detailed description of the story..."
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="min-h-[100px] resize-none"
            />
          </div>

          {/* Story Points and Priority */}
          <div className="grid grid-cols-2 gap-4">
            {/* Story Points */}
            <div className="space-y-2">
              <Label htmlFor="story_point" className="text-sm font-semibold flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                Story Points
              </Label>
              <Select
                value={formData.story_point?.toString()}
                onValueChange={(value) => setFormData(prev => ({
                  ...prev,
                  story_point: parseInt(value)
                }))}
              >
                <SelectTrigger id="story_point" className="h-10">
                  <SelectValue placeholder="Not estimated" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 (1 day)</SelectItem>
                  <SelectItem value="2">2 (2 days)</SelectItem>
                  <SelectItem value="3">3 (3 days)</SelectItem>
                  <SelectItem value="5">5 (1 week)</SelectItem>
                  <SelectItem value="8">8 (2 weeks)</SelectItem>
                  <SelectItem value="13">13 (Too large - split!)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <Label htmlFor="priority" className="text-sm font-semibold flex items-center gap-1.5">
                <Flag className="w-3.5 h-3.5" />
                Priority
              </Label>
              <Select
                value={formData.priority || "Medium"}
                onValueChange={(value: "High" | "Medium" | "Low") =>
                  setFormData(prev => ({ ...prev, priority: value }))
                }
              >
                <SelectTrigger id="priority" className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="High">High - Must have</SelectItem>
                  <SelectItem value="Medium">Medium - Should have</SelectItem>
                  <SelectItem value="Low">Low - Nice to have</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Acceptance Criteria */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Acceptance Criteria</Label>

            {/* Existing criteria */}
            {formData.acceptance_criteria.length > 0 && (
              <div className="space-y-2 mb-2">
                {formData.acceptance_criteria.map((criteria, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-xs font-semibold text-muted-foreground mt-0.5">
                      {index + 1}.
                    </span>
                    <span className="flex-1 text-sm text-foreground">{criteria}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveCriteria(index)}
                      className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new criteria */}
            <div className="flex gap-2">
              <Input
                placeholder="Given [context], When [action], Then [outcome]"
                value={currentCriteria}
                onChange={(e) => setCurrentCriteria(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleAddCriteria()
                  }
                }}
                className="h-9 text-sm"
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleAddCriteria}
                className="h-9 px-3 text-xs"
              >
                Add
              </Button>
            </div>
          </div>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            * Required fields
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                handleReset()
                onOpenChange(false)
              }}
              className="h-9"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!formData.title.trim()}
              className="h-9"
            >
              Create Story
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
