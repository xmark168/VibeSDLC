import { useEffect, useState, useRef } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Plus, X, Upload, ImageIcon } from "lucide-react"
import type { PersonaTemplate, PersonaCreate, RoleType } from "@/types/persona"
import { roleTypeLabels } from "@/types/persona"
import { useCreatePersona, useUpdatePersona } from "@/queries/personas"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import toast from "react-hot-toast"

const personaFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  role_type: z.enum(["team_leader", "business_analyst", "developer", "tester"]),
  avatar: z.string().nullable().optional(),
  personality_traits: z.array(z.string()).default([]),
  communication_style: z.string().min(1, "Communication style is required").max(500),
  display_order: z.coerce.number().int().min(0).default(0),
  persona_metadata: z.record(z.string(), z.unknown()).optional(),
})

type PersonaFormValues = z.infer<typeof personaFormSchema>

const jsonPersonaSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  role_type: z.enum(["team_leader", "business_analyst", "developer", "tester"]),
  avatar: z.string().nullable().optional(),
  personality_traits: z.array(z.string()).optional().default([]),
  communication_style: z.string().min(1, "Communication style is required").max(500),
  display_order: z.number().int().min(0, "Display order must be non-negative").optional().default(0),
  persona_metadata: z.record(z.string(), z.unknown()).optional(),
})

interface PersonaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  persona?: PersonaTemplate
  onSuccess?: () => void
}

function AvatarUpload({
  value,
  onChange,
}: {
  value?: string | null
  onChange: (value: string | null) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file")
      return
    }

    if (file.size > 2 * 1024 * 1024) {
      toast.error("Image must be less than 2MB")
      return
    }

    const reader = new FileReader()
    reader.onload = (event) => {
      onChange(event.target?.result as string)
    }
    reader.readAsDataURL(file)
  }

  const handleRemove = () => {
    onChange(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar className="w-16 h-16 border-2 border-dashed border-muted-foreground/30">
        {value ? (
          <AvatarImage src={value} alt="Avatar preview" />
        ) : (
          <AvatarFallback className="bg-muted">
            <ImageIcon className="w-6 h-6 text-muted-foreground" />
          </AvatarFallback>
        )}
      </Avatar>
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-4 h-4 mr-1" />
            Upload
          </Button>
          {value && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRemove}
            >
              <X className="w-4 h-4 mr-1" />
              Remove
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">PNG, JPG up to 2MB</p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  )
}

export function PersonaDialog({ open, onOpenChange, persona, onSuccess }: PersonaDialogProps) {
  const isEditing = !!persona
  const [traitInput, setTraitInput] = useState("")
  const [activeTab, setActiveTab] = useState<string>("form")
  const [jsonInput, setJsonInput] = useState("")
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [jsonAvatar, setJsonAvatar] = useState<string | null>(null)
  
  const createPersona = useCreatePersona()
  const updatePersona = useUpdatePersona()

  const form = useForm<PersonaFormValues>({
    resolver: zodResolver(personaFormSchema) as any,
    defaultValues: {
      name: "",
      role_type: "developer",
      avatar: null,
      personality_traits: [],
      communication_style: "",
      display_order: 0,
      persona_metadata: {},
    },
  })

  useEffect(() => {
    if (persona && open) {
      const values = {
        name: persona.name,
        role_type: persona.role_type as RoleType,
        avatar: persona.avatar || null,
        personality_traits: persona.personality_traits || [],
        communication_style: persona.communication_style,
        display_order: persona.display_order,
        persona_metadata: persona.persona_metadata || {},
      }
      form.reset(values)
      setJsonInput(JSON.stringify({
        name: persona.name,
        role_type: persona.role_type,
        personality_traits: persona.personality_traits || [],
        communication_style: persona.communication_style,
        display_order: persona.display_order,
        persona_metadata: persona.persona_metadata || {},
      }, null, 2))
      setJsonAvatar(persona.avatar || null)
    } else if (!open) {
      form.reset({
        name: "",
        role_type: "developer",
        avatar: null,
        personality_traits: [],
        communication_style: "",
        display_order: 0,
        persona_metadata: {},
      })
      setJsonInput(JSON.stringify({
        name: "",
        role_type: "developer",
        personality_traits: [],
        communication_style: "",
        display_order: 0,
        persona_metadata: {},
      }, null, 2))
      setJsonAvatar(null)
      setJsonError(null)
      setActiveTab("form")
    }
  }, [persona, open, form])

  const handleAddTrait = () => {
    if (traitInput.trim()) {
      const currentTraits = form.getValues("personality_traits")
      if (!currentTraits.includes(traitInput.trim())) {
        form.setValue("personality_traits", [...currentTraits, traitInput.trim()])
      }
      setTraitInput("")
    }
  }

  const handleRemoveTrait = (trait: string) => {
    const currentTraits = form.getValues("personality_traits")
    form.setValue(
      "personality_traits",
      currentTraits.filter((t) => t !== trait)
    )
  }

  const onSubmit = async (data: PersonaFormValues) => {
    const payload = {
      name: data.name,
      role_type: data.role_type,
      avatar: data.avatar || null,
      personality_traits: data.personality_traits || [],
      communication_style: data.communication_style,
      display_order: data.display_order ?? 0,
      persona_metadata: data.persona_metadata || {},
    }

    try {
      if (isEditing) {
        await updatePersona.mutateAsync({
          personaId: persona.id,
          data: payload,
        })
      } else {
        await createPersona.mutateAsync(payload)
      }
      onOpenChange(false)
      onSuccess?.()
    } catch (error: any) {
      // Error handled by mutation hooks - keep modal open
    }
  }

  const handleJsonSubmit = async () => {
    setJsonError(null)
    
    let parsed: any
    try {
      parsed = JSON.parse(jsonInput)
    } catch {
      setJsonError("Invalid JSON format")
      return
    }

    let validated: any
    try {
      validated = jsonPersonaSchema.parse(parsed)
    } catch (error: any) {
      if (error?.errors) {
        const zodErrors = error.errors.map((e: any) => `${e.path.join(".")}: ${e.message}`).join(", ")
        setJsonError(zodErrors)
      } else {
        setJsonError("Validation failed")
      }
      return
    }
    
    const payload = {
      ...validated,
      avatar: jsonAvatar,
    }

    try {
      if (isEditing) {
        await updatePersona.mutateAsync({
          personaId: persona.id,
          data: payload,
        })
      } else {
        await createPersona.mutateAsync(payload)
      }
      onOpenChange(false)
      onSuccess?.()
    } catch (error: any) {
      setJsonError(error?.message || "Failed to save persona")
      // Keep modal open on error
    }
  }

  const isPending = createPersona.isPending || updatePersona.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Persona" : "Create Persona"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the persona template properties."
              : "Create a new persona template for agents to use."}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="form">Form</TabsTrigger>
            <TabsTrigger value="json">JSON</TabsTrigger>
          </TabsList>

          <TabsContent value="form" className="mt-4">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                {/* Avatar Upload */}
                <FormField
                  control={form.control}
                  name="avatar"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Avatar</FormLabel>
                      <FormControl>
                        <AvatarUpload
                          value={field.value}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormDescription>
                        Upload an avatar image for this persona
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-4">
                  {/* Name */}
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g., Strategic Visionary" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Role Type */}
                  <FormField
                    control={form.control}
                    name="role_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Role Type</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select role type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {Object.entries(roleTypeLabels).map(([value, label]) => (
                              <SelectItem key={value} value={value}>
                                {label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Communication Style */}
                <FormField
                  control={form.control}
                  name="communication_style"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Communication Style</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="e.g., inspirational and goal-oriented"
                          rows={3}
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Describe how this persona communicates with team members
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Personality Traits */}
                <FormField
                  control={form.control}
                  name="personality_traits"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Personality Traits</FormLabel>
                      <div className="space-y-2">
                        <div className="flex gap-2">
                          <Input
                            placeholder="Add a trait (e.g., visionary, analytical)"
                            value={traitInput}
                            onChange={(e) => setTraitInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault()
                                handleAddTrait()
                              }
                            }}
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={handleAddTrait}
                          >
                            <Plus className="w-4 h-4" />
                          </Button>
                        </div>
                        
                        {field.value.length > 0 && (
                          <div className="flex flex-wrap gap-2 p-3 border rounded-md bg-muted/30">
                            {field.value.map((trait) => (
                              <Badge key={trait} variant="secondary" className="gap-1">
                                {trait}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveTrait(trait)}
                                  className="ml-1 hover:text-destructive"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <FormDescription>
                        Press Enter or click + to add traits
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Display Order */}
                <FormField
                  control={form.control}
                  name="display_order"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Display Order</FormLabel>
                      <FormControl>
                        <Input type="number" min={0} {...field} />
                      </FormControl>
                      <FormDescription>
                        Lower numbers appear first (0 = highest priority)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => onOpenChange(false)}
                    disabled={isPending}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isPending}>
                    {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    {isEditing ? "Update" : "Create"}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </TabsContent>

          <TabsContent value="json" className="mt-4 space-y-6">
            {/* Avatar Upload for JSON tab */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Avatar</label>
              <AvatarUpload
                value={jsonAvatar}
                onChange={setJsonAvatar}
              />
              <p className="text-xs text-muted-foreground">
                Upload an avatar image for this persona
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">JSON Configuration</label>
              <Textarea
                value={jsonInput}
                onChange={(e) => {
                  setJsonInput(e.target.value)
                  setJsonError(null)
                }}
                placeholder={`{
  "name": "Strategic Visionary",
  "role_type": "team_leader",
  "personality_traits": ["visionary", "analytical"],
  "communication_style": "inspirational and goal-oriented",
  "display_order": 0,
  "persona_metadata": {}
}`}
                rows={15}
                className="font-mono text-sm"
              />
              {jsonError && (
                <p className="text-sm text-destructive">{jsonError}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Provide persona data in JSON format. Required fields: name, role_type, communication_style
              </p>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button onClick={handleJsonSubmit} disabled={isPending}>
                {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isEditing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
