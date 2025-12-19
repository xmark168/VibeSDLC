import {
  Check,
  ChevronsUpDown,
  ClipboardPaste,
  FileText,
  Flag,
  Layers,
  Plus,
  Upload,
  X,
  Zap,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { storiesApi } from "@/apis/stories"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { Story, StoryFormData } from "@/types"
import { CreateEpicDialog, type NewEpicData } from "./create-epic-dialog"

export type { StoryFormData }

export interface StoryEditData {
  id: string
  title: string
  description?: string
  type: "UserStory"
  story_point?: number
  priority?: number
  rank?: number
  acceptance_criteria?: string[]
  requirements?: string[]
  dependencies?: string[]
  epic_id?: string
}

interface CreateStoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateStory: (story: StoryFormData) => void
  onUpdateStory?: (storyId: string, story: StoryFormData) => void
  projectId?: string
  editingStory?: StoryEditData | null
}

const getDefaultFormData = (): StoryFormData => ({
  title: "",
  description: "",
  type: "UserStory",
  story_point: 1,
  priority: "Medium",
  acceptance_criteria: [],
  requirements: [],
  dependencies: [],
  epic_id: undefined,
})

export function CreateStoryDialog({
  open,
  onOpenChange,
  onCreateStory,
  onUpdateStory,
  projectId,
  editingStory,
}: CreateStoryDialogProps) {
  const isEditMode = !!editingStory

  const [formData, setFormData] = useState<StoryFormData>(getDefaultFormData())

  const [currentCriteria, setCurrentCriteria] = useState("")
  const [currentRequirement, setCurrentRequirement] = useState("")
  const [dependencyPopoverOpen, setDependencyPopoverOpen] = useState(false)
  const [epicPopoverOpen, setEpicPopoverOpen] = useState(false)
  const [existingStories, setExistingStories] = useState<Story[]>([])
  const [availableEpics, setAvailableEpics] = useState<
    { id: string; code?: string; title: string }[]
  >([])
  const [loadingStories, setLoadingStories] = useState(false)
  const [loadingEpics, setLoadingEpics] = useState(false)
  const [showCreateEpicDialog, setShowCreateEpicDialog] = useState(false)
  const [newEpicData, setNewEpicData] = useState<NewEpicData | null>(null)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [importText, setImportText] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Parse markdown story format
  const parseMarkdownStory = (
    markdown: string,
  ): Partial<StoryFormData> & {
    dependency_codes?: string[]
    epic_code?: string
  } => {
    const result: Partial<StoryFormData> & {
      dependency_codes?: string[]
      epic_code?: string
    } = {}

    // Extract title from ### Title section
    const titleMatch = markdown.match(/###\s*Title\s*\n([\s\S]*?)(?=###|$)/i)
    if (titleMatch) {
      result.title = titleMatch[1].trim()
    }

    // Extract epic code from ### Epic section
    const epicMatch = markdown.match(/###\s*Epic\s*\n([\s\S]*?)(?=###|$)/i)
    if (epicMatch) {
      result.epic_code = epicMatch[1].trim()
    }

    // Extract story point from ### Story points section
    const storyPointMatch = markdown.match(
      /###\s*Story\s*points?\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (storyPointMatch) {
      const point = parseInt(storyPointMatch[1].trim(), 10)
      if ([1, 2, 3, 5, 8, 13].includes(point)) {
        result.story_point = point
      }
    }

    // Extract priority from ### Priority section
    const priorityMatch = markdown.match(
      /###\s*Priority\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (priorityMatch) {
      const priorityText = priorityMatch[1].trim().toLowerCase()
      if (priorityText.includes("high") || priorityText.includes("must")) {
        result.priority = "High"
      } else if (
        priorityText.includes("medium") ||
        priorityText.includes("should")
      ) {
        result.priority = "Medium"
      } else if (
        priorityText.includes("low") ||
        priorityText.includes("nice")
      ) {
        result.priority = "Low"
      }
    }

    // Extract description from ### Description section
    const descriptionMatch = markdown.match(
      /###\s*Description\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (descriptionMatch) {
      result.description = descriptionMatch[1].trim()
    }

    // Extract requirements from ### Requirements section
    const requirementsMatch = markdown.match(
      /###\s*Requirements\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (requirementsMatch) {
      const requirementsText = requirementsMatch[1]
      const requirements = requirementsText
        .split("\n")
        .filter((line) => line.trim().startsWith("-"))
        .map((line) => line.replace(/^-\s*/, "").trim())
        .filter((line) => line.length > 0)
      if (requirements.length > 0) {
        result.requirements = requirements
      }
    }

    // Extract acceptance criteria from ### Acceptance Criteria section
    const criteriaMatch = markdown.match(
      /###\s*Acceptance\s*Criteria\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (criteriaMatch) {
      const criteriaText = criteriaMatch[1]
      const criteria = criteriaText
        .split("\n")
        .filter((line) => line.trim().startsWith("-"))
        .map((line) => line.replace(/^-\s*/, "").trim())
        .filter((line) => line.length > 0)
      if (criteria.length > 0) {
        result.acceptance_criteria = criteria
      }
    }

    // Extract dependencies from ### Dependencies section
    const dependenciesMatch = markdown.match(
      /###\s*Dependencies\s*\n([\s\S]*?)(?=###|$)/i,
    )
    if (dependenciesMatch) {
      const dependenciesText = dependenciesMatch[1]
      const codes = dependenciesText
        .split("\n")
        .filter((line) => line.trim().startsWith("-"))
        .map((line) => line.replace(/^-\s*/, "").trim())
        .filter((line) => line.length > 0)
      if (codes.length > 0) {
        result.dependency_codes = codes
      }
    }

    return result
  }

  // Match dependency codes to story IDs
  const matchDependencyCodesToIds = (codes: string[]): string[] => {
    const matchedIds: string[] = []
    for (const code of codes) {
      const story = existingStories.find((s) => s.story_code === code)
      if (story) {
        matchedIds.push(story.id)
      }
    }
    return matchedIds
  }

  // Match epic code to epic ID
  const matchEpicCodeToId = (code: string): string | undefined => {
    const epic = availableEpics.find((e) => e.code === code)
    return epic?.id
  }

  // Handle import from pasted text
  const handleImportFromText = () => {
    if (!importText.trim()) return

    const parsed = parseMarkdownStory(importText)
    const dependencyIds = parsed.dependency_codes
      ? matchDependencyCodesToIds(parsed.dependency_codes)
      : []
    const epicId = parsed.epic_code
      ? matchEpicCodeToId(parsed.epic_code)
      : undefined

    setFormData((prev) => ({
      ...prev,
      title: parsed.title || prev.title,
      description: parsed.description || prev.description,
      requirements: parsed.requirements || prev.requirements,
      acceptance_criteria:
        parsed.acceptance_criteria || prev.acceptance_criteria,
      dependencies:
        dependencyIds.length > 0 ? dependencyIds : prev.dependencies,
      epic_id: epicId || prev.epic_id,
      story_point: parsed.story_point || prev.story_point,
      priority: parsed.priority || prev.priority,
    }))

    setShowImportDialog(false)
    setImportText("")
  }

  // Handle import from .md file
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      if (content) {
        const parsed = parseMarkdownStory(content)
        const dependencyIds = parsed.dependency_codes
          ? matchDependencyCodesToIds(parsed.dependency_codes)
          : []
        const epicId = parsed.epic_code
          ? matchEpicCodeToId(parsed.epic_code)
          : undefined

        setFormData((prev) => ({
          ...prev,
          title: parsed.title || prev.title,
          description: parsed.description || prev.description,
          requirements: parsed.requirements || prev.requirements,
          acceptance_criteria:
            parsed.acceptance_criteria || prev.acceptance_criteria,
          dependencies:
            dependencyIds.length > 0 ? dependencyIds : prev.dependencies,
          epic_id: epicId || prev.epic_id,
          story_point: parsed.story_point || prev.story_point,
          priority: parsed.priority || prev.priority,
        }))
      }
    }
    reader.readAsText(file)

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  // Populate form data when editing
  useEffect(() => {
    if (open && editingStory) {
      const priorityMap: Record<number, "High" | "Medium" | "Low"> = {
        1: "High",
        2: "Medium",
        3: "Low",
      }
      setFormData({
        title: editingStory.title,
        description: editingStory.description || "",
        type: editingStory.type,
        story_point: editingStory.story_point || 1,
        priority: editingStory.priority
          ? priorityMap[editingStory.priority] || "Medium"
          : "Medium",
        acceptance_criteria: editingStory.acceptance_criteria || [],
        requirements: editingStory.requirements || [],
        dependencies: editingStory.dependencies || [],
        epic_id: editingStory.epic_id,
      })
    } else if (open && !editingStory) {
      setFormData(getDefaultFormData())
    }
  }, [open, editingStory])

  // Fetch existing stories and epics when dialog opens
  useEffect(() => {
    if (open && projectId) {
      // Load stories for dependencies
      setLoadingStories(true)
      storiesApi
        .list(projectId, { limit: 100 })
        .then((result) => {
          setExistingStories(result.data || [])
        })
        .catch((_err) => {
          setExistingStories([])
        })
        .finally(() => setLoadingStories(false))

      // Load epics directly from API
      setLoadingEpics(true)
      storiesApi
        .listEpics(projectId)
        .then((result) => {
          setAvailableEpics(
            (result.data || []).map((epic) => ({
              id: epic.id,
              code: epic.epic_code,
              title: epic.title,
            })),
          )
        })
        .catch((_err) => {
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

    // Include new epic data if creating new epic
    const submitData = newEpicData
      ? {
          ...formData,
          new_epic_title: newEpicData.title,
          new_epic_domain: newEpicData.domain,
          new_epic_description: newEpicData.description,
          epic_id: undefined,
        }
      : formData

    if (isEditMode && editingStory && onUpdateStory) {
      onUpdateStory(editingStory.id, submitData)
    } else {
      onCreateStory(submitData)
    }
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
      epic_id: undefined,
    })
    setCurrentCriteria("")
    setCurrentRequirement("")
    setDependencyPopoverOpen(false)
    setEpicPopoverOpen(false)
    setNewEpicData(null)
  }

  const handleCreateEpic = (epicData: NewEpicData) => {
    setNewEpicData(epicData)
    setFormData((prev) => ({ ...prev, epic_id: undefined }))
  }

  const handleAddCriteria = () => {
    if (currentCriteria.trim()) {
      setFormData((prev) => ({
        ...prev,
        acceptance_criteria: [
          ...prev.acceptance_criteria,
          currentCriteria.trim(),
        ],
      }))
      setCurrentCriteria("")
    }
  }

  const handleRemoveCriteria = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      acceptance_criteria: prev.acceptance_criteria.filter(
        (_, i) => i !== index,
      ),
    }))
  }

  const handleAddRequirement = () => {
    if (currentRequirement.trim()) {
      setFormData((prev) => ({
        ...prev,
        requirements: [...prev.requirements, currentRequirement.trim()],
      }))
      setCurrentRequirement("")
    }
  }

  const handleRemoveRequirement = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      requirements: prev.requirements.filter((_, i) => i !== index),
    }))
  }

  const handleToggleDependency = (storyId: string) => {
    setFormData((prev) => {
      const isSelected = prev.dependencies.includes(storyId)
      return {
        ...prev,
        dependencies: isSelected
          ? prev.dependencies.filter((id) => id !== storyId)
          : [...prev.dependencies, storyId],
      }
    })
  }

  const handleRemoveDependency = (storyId: string) => {
    setFormData((prev) => ({
      ...prev,
      dependencies: prev.dependencies.filter((id) => id !== storyId),
    }))
  }

  // Get story title by ID for display
  const getStoryTitle = (storyId: string) => {
    const story = existingStories.find((s) => s.id === storyId)
    return story?.title || storyId
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-bold">
              {isEditMode ? "Edit Story" : "Create New Story"}
            </DialogTitle>
            {!isEditMode && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="h-8 gap-1.5">
                    <Upload className="w-4 h-4" />
                    Import
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setShowImportDialog(true)}>
                    <ClipboardPaste className="w-4 h-4 mr-2" />
                    Paste Text
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Select .md/.txt File
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
          <DialogDescription>
            {isEditMode
              ? "Update the story details below"
              : "Fill in the details below to create a new story on the Kanban board"}
          </DialogDescription>
        </DialogHeader>

        {/* Hidden file input for .md upload */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".md,.markdown,.txt"
          onChange={handleFileUpload}
          className="hidden"
        />

        <Separator />

        <div className="space-y-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title" className="text-sm font-semibold">
              Story Title *
            </Label>
            <Input
              id="title"
              placeholder="As a [role], I want [feature] so that [benefit]"
              value={formData.title}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, title: e.target.value }))
              }
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
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              className="min-h-[100px] resize-none"
            />
          </div>

          {/* Epic */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" />
              Epic
            </Label>

            {/* Show new epic info if created */}
            {newEpicData ? (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/5 border border-primary/20">
                <Badge
                  variant="outline"
                  className="font-mono text-xs bg-primary/10"
                >
                  NEW
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {newEpicData.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {newEpicData.domain}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setNewEpicData(null)}
                  className="h-8 w-8 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ) : (
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
                        {availableEpics.find((e) => e.id === formData.epic_id)
                          ?.code && (
                          <Badge
                            variant="outline"
                            className="font-mono text-xs"
                          >
                            {
                              availableEpics.find(
                                (e) => e.id === formData.epic_id,
                              )?.code
                            }
                          </Badge>
                        )}
                        <span className="truncate">
                          {availableEpics.find((e) => e.id === formData.epic_id)
                            ?.title || "Select epic..."}
                        </span>
                      </span>
                    ) : (
                      "Select epic (optional)..."
                    )}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search epics..." />
                    <CommandList className="max-h-[250px] overflow-y-auto">
                      <CommandEmpty>No epic found.</CommandEmpty>
                      <CommandGroup>
                        {/* Create new epic option */}
                        <CommandItem
                          value="__create_new__"
                          onSelect={() => {
                            setShowCreateEpicDialog(true)
                            setEpicPopoverOpen(false)
                          }}
                          className="cursor-pointer text-primary"
                        >
                          <Plus className="mr-2 h-4 w-4 flex-shrink-0" />
                          <span className="font-medium">Tạo Epic mới...</span>
                        </CommandItem>

                        <Separator className="my-1" />

                        {/* None option */}
                        <CommandItem
                          value="none"
                          onSelect={() => {
                            setFormData((prev) => ({
                              ...prev,
                              epic_id: undefined,
                            }))
                            setEpicPopoverOpen(false)
                          }}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4 flex-shrink-0",
                              !formData.epic_id ? "opacity-100" : "opacity-0",
                            )}
                          />
                          <span className="text-muted-foreground">No Epic</span>
                        </CommandItem>

                        {/* Existing epics */}
                        {availableEpics.map((epic) => (
                          <CommandItem
                            key={epic.id}
                            value={epic.title}
                            onSelect={() => {
                              setFormData((prev) => ({
                                ...prev,
                                epic_id: epic.id,
                              }))
                              setNewEpicData(null)
                              setEpicPopoverOpen(false)
                            }}
                            className="cursor-pointer"
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4 flex-shrink-0",
                                formData.epic_id === epic.id
                                  ? "opacity-100"
                                  : "opacity-0",
                              )}
                            />
                            <div className="flex items-center gap-2">
                              {epic.code && (
                                <Badge
                                  variant="outline"
                                  className="font-mono text-xs"
                                >
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
            )}
          </div>

          {/* Story Points and Priority */}
          <div className="grid grid-cols-2 gap-4">
            {/* Story Points */}
            <div className="space-y-2">
              <Label
                htmlFor="story_point"
                className="text-sm font-semibold flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5" />
                Story Points
              </Label>
              <Select
                value={formData.story_point?.toString()}
                onValueChange={(value) =>
                  setFormData((prev) => ({
                    ...prev,
                    story_point: parseInt(value, 10),
                  }))
                }
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
                  <SelectItem value="13">
                    13 - XXL (Too large - split!)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <Label
                htmlFor="priority"
                className="text-sm font-semibold flex items-center gap-1.5"
              >
                <Flag className="w-3.5 h-3.5" />
                Priority
              </Label>
              <Select
                value={formData.priority || "Medium"}
                onValueChange={(value: "High" | "Medium" | "Low") =>
                  setFormData((prev) => ({ ...prev, priority: value }))
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
                    <span className="flex-1 text-sm text-foreground">
                      {criteria}
                    </span>
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
                    <span className="flex-1 text-sm text-foreground">
                      {requirement}
                    </span>
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
            <Popover
              open={dependencyPopoverOpen}
              onOpenChange={setDependencyPopoverOpen}
            >
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={dependencyPopoverOpen}
                  className="w-full justify-between h-9 text-sm font-normal"
                  disabled={loadingStories || existingStories.length === 0}
                >
                  {loadingStories
                    ? "Loading stories..."
                    : existingStories.length === 0
                      ? "No stories available"
                      : "Select dependencies..."}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search stories..." />
                  <CommandList className="max-h-[200px] overflow-y-auto">
                    <CommandEmpty>No story found.</CommandEmpty>
                    <CommandGroup>
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
                              formData.dependencies.includes(story.id)
                                ? "opacity-100"
                                : "opacity-0",
                            )}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm truncate">{story.title}</p>
                            <p className="text-xs text-muted-foreground">
                              {story.story_code && `${story.story_code} • `}
                              {story.type} • {story.status}
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
          <div className="text-xs text-muted-foreground">* Required fields</div>
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
              {isEditMode ? "Update Story" : "Create Story"}
            </Button>
          </div>
        </div>
      </DialogContent>

      {/* Create Epic Dialog */}
      <CreateEpicDialog
        open={showCreateEpicDialog}
        onOpenChange={setShowCreateEpicDialog}
        onCreateEpic={handleCreateEpic}
      />

      {/* Import Text Dialog */}
      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Story from Markdown</DialogTitle>
            <DialogDescription>
              Paste your story in markdown format below. Use ### sections for
              each field.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              placeholder={`### Title
As a [role], I want [feature] so that [benefit]

### Epic
EPIC-001

### Description
Detailed description of the story...

### Requirements
- Requirement 1
- Requirement 2

### Acceptance Criteria
- Given [context], When [action], Then [outcome]
- Given [context], When [action], Then [outcome]

### Dependencies
- EPIC-001-US-001
- EPIC-001-US-002

### Story points
5

### Priority
High`}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              className="min-h-[300px] font-mono text-sm"
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setShowImportDialog(false)
                  setImportText("")
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleImportFromText}
                disabled={!importText.trim()}
              >
                Import
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Dialog>
  )
}
