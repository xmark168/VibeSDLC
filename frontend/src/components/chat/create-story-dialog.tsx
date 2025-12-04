import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Zap, Flag, X, Link2, ChevronsUpDown, Check, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { storiesApi } from "@/apis/stories"
import type { StoryFormData, Story } from "@/types"

export type { StoryFormData }

interface CreateStoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateStory: (story: StoryFormData) => void
  projectId?: string
}

export function CreateStoryDialog({ open, onOpenChange, onCreateStory, projectId }: CreateStoryDialogProps) {
  const [formData, setFormData] = useState<StoryFormData>({
    title: "",
    description: "",
    type: "UserStory",
    story_point: 1,
    priority: "Medium",
    acceptance_criteria: [],
    requirements: [],
    dependencies: [],
    epic_id: undefined
  })

  const [currentCriteria, setCurrentCriteria] = useState("")
  const [currentRequirement, setCurrentRequirement] = useState("")
  const [dependencyPopoverOpen, setDependencyPopoverOpen] = useState(false)
  const [epicPopoverOpen, setEpicPopoverOpen] = useState(false)
  const [existingStories, setExistingStories] = useState<Story[]>([])
  const [availableEpics, setAvailableEpics] = useState<{ id: string; code?: string; title: string }[]>([])
  const [loadingStories, setLoadingStories] = useState(false)
  const [loadingEpics, setLoadingEpics] = useState(false)

  // Fetch existing stories and epics when dialog opens
  useEffect(() => {
    if (open && projectId) {
      // Load stories for dependencies
      setLoadingStories(true)
      storiesApi.list(projectId, { limit: 100 })
        .then(result => {
          setExistingStories(result.data || [])
        })
        .catch(err => {
          console.error("Failed to load stories:", err)
          setExistingStories([])
        })
        .finally(() => setLoadingStories(false))
      
      // Load epics directly from API
      setLoadingEpics(true)
      storiesApi.listEpics(projectId)
        .then(result => {
          setAvailableEpics((result.data || []).map(epic => ({
            id: epic.id,
            code: epic.epic_code,
            title: epic.title
          })))
        })
        .catch(err => {
          console.error("Failed to load epics:", err)
          setAvailableEpics([])
        })
        .finally(() => setLoadingEpics(false))
    }
  }, [open, projectId])

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
      story_point: 1,
      priority: "Medium",
      acceptance_criteria: [],
      requirements: [],
      dependencies: [],
      epic_id: undefined
    })
    setCurrentCriteria("")
    setCurrentRequirement("")
    setDependencyPopoverOpen(false)
    setEpicPopoverOpen(false)
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

  const handleAddRequirement = () => {
    if (currentRequirement.trim()) {
      setFormData(prev => ({
        ...prev,
        requirements: [...prev.requirements, currentRequirement.trim()]
      }))
      setCurrentRequirement("")
    }
  }

  const handleRemoveRequirement = (index: number) => {
    setFormData(prev => ({
      ...prev,
      requirements: prev.requirements.filter((_, i) => i !== index)
    }))
  }

  const handleToggleDependency = (storyId: string) => {
    setFormData(prev => {
      const isSelected = prev.dependencies.includes(storyId)
      return {
        ...prev,
        dependencies: isSelected 
          ? prev.dependencies.filter(id => id !== storyId)
          : [...prev.dependencies, storyId]
      }
    })
  }

  const handleRemoveDependency = (storyId: string) => {
    setFormData(prev => ({
      ...prev,
      dependencies: prev.dependencies.filter(id => id !== storyId)
    }))
  }

  // Get story title by ID for display
  const getStoryTitle = (storyId: string) => {
    const story = existingStories.find(s => s.id === storyId)
    return story?.title || storyId
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

          {/* Epic */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" />
              Epic
            </Label>
            <Popover open={epicPopoverOpen} onOpenChange={setEpicPopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={epicPopoverOpen}
                  className="w-full justify-between h-10 text-sm font-normal"
                  disabled={loadingEpics}
                >
                  {loadingEpics ? (
                    "Loading epics..."
                  ) : formData.epic_id ? (
                    <span className="flex items-center gap-2">
                      {availableEpics.find(e => e.id === formData.epic_id)?.code && (
                        <Badge variant="outline" className="font-mono text-xs">
                          {availableEpics.find(e => e.id === formData.epic_id)?.code}
                        </Badge>
                      )}
                      <span className="truncate">
                        {availableEpics.find(e => e.id === formData.epic_id)?.title || "Select epic..."}
                      </span>
                    </span>
                  ) : availableEpics.length === 0 ? (
                    "No epics available"
                  ) : (
                    "Select epic (optional)..."
                  )}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search epics..." />
                  <CommandList>
                    <CommandEmpty>No epic found.</CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-y-auto">
                      {/* None option */}
                      <CommandItem
                        value="none"
                        onSelect={() => {
                          setFormData(prev => ({ ...prev, epic_id: undefined }))
                          setEpicPopoverOpen(false)
                        }}
                        className="cursor-pointer"
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4 flex-shrink-0",
                            !formData.epic_id ? "opacity-100" : "opacity-0"
                          )}
                        />
                        <span className="text-muted-foreground">No Epic</span>
                      </CommandItem>
                      {availableEpics.map((epic) => (
                        <CommandItem
                          key={epic.id}
                          value={epic.title}
                          onSelect={() => {
                            setFormData(prev => ({ ...prev, epic_id: epic.id }))
                            setEpicPopoverOpen(false)
                          }}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4 flex-shrink-0",
                              formData.epic_id === epic.id ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <div className="flex items-center gap-2">
                            {epic.code && (
                              <Badge variant="outline" className="font-mono text-xs">
                                {epic.code}
                              </Badge>
                            )}
                            <span className="truncate">{epic.title}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
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
                  <SelectItem value="1">1 - XS (Extra Small)</SelectItem>
                  <SelectItem value="2">2 - S (Small)</SelectItem>
                  <SelectItem value="3">3 - M (Medium)</SelectItem>
                  <SelectItem value="5">5 - L (Large)</SelectItem>
                  <SelectItem value="8">8 - XL (Extra Large)</SelectItem>
                  <SelectItem value="13">13 - XXL (Too large - split!)</SelectItem>
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

          {/* Requirements */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Requirements</Label>

            {/* Existing requirements */}
            {formData.requirements.length > 0 && (
              <div className="space-y-2 mb-2">
                {formData.requirements.map((requirement, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-xs font-semibold text-muted-foreground mt-0.5">
                      {index + 1}.
                    </span>
                    <span className="flex-1 text-sm text-foreground">{requirement}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveRequirement(index)}
                      className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new requirement */}
            <div className="flex gap-2">
              <Input
                placeholder="Specific requirement for developers..."
                value={currentRequirement}
                onChange={(e) => setCurrentRequirement(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleAddRequirement()
                  }
                }}
                className="h-9 text-sm"
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleAddRequirement}
                className="h-9 px-3 text-xs"
              >
                Add
              </Button>
            </div>
          </div>

          {/* Dependencies */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold flex items-center gap-1.5">
              Dependencies
            </Label>
            <p className="text-xs text-muted-foreground">
              Select stories that must be completed before this story can start
            </p>

            {/* Selected dependencies */}
            {formData.dependencies.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {formData.dependencies.map((depId) => (
                  <Badge
                    key={depId}
                    variant="outline"
                    className="bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-300 border-orange-200/50 dark:border-orange-800/50 text-xs flex items-center gap-1 max-w-[250px]"
                  >
                    <span className="truncate">{getStoryTitle(depId)}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveDependency(depId)}
                      className="ml-1 hover:text-destructive transition-colors flex-shrink-0"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}

            {/* Story selector */}
            <Popover open={dependencyPopoverOpen} onOpenChange={setDependencyPopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={dependencyPopoverOpen}
                  className="w-full justify-between h-9 text-sm font-normal"
                  disabled={loadingStories || existingStories.length === 0}
                >
                  {loadingStories ? (
                    "Loading stories..."
                  ) : existingStories.length === 0 ? (
                    "No stories available"
                  ) : (
                    "Select dependencies..."
                  )}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search stories..." />
                  <CommandList>
                    <CommandEmpty>No story found.</CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-y-auto">
                      {existingStories.map((story) => (
                        <CommandItem
                          key={story.id}
                          value={story.title}
                          onSelect={() => handleToggleDependency(story.id)}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4 flex-shrink-0",
                              formData.dependencies.includes(story.id) ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm truncate">{story.title}</p>
                            <p className="text-xs text-muted-foreground">
                              {story.story_code && `${story.story_code} • `}{story.type} • {story.status}
                            </p>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
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
