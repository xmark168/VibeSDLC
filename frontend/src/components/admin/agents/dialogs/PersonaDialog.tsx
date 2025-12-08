import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Plus, X } from "lucide-react"
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
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const personaFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  role_type: z.enum(["team_leader", "business_analyst", "developer", "tester"]),
  personality_traits: z.array(z.string()).default([]),
  communication_style: z.string().min(1, "Communication style is required").max(500),
  display_order: z.coerce.number().int().min(0).default(0),
  persona_metadata: z.record(z.any()).optional(),
})

type PersonaFormValues = z.infer<typeof personaFormSchema>

interface PersonaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  persona?: PersonaTemplate
  onSuccess?: () => void
}

export function PersonaDialog({ open, onOpenChange, persona, onSuccess }: PersonaDialogProps) {
  const isEditing = !!persona
  const [traitInput, setTraitInput] = useState("")
  
  const createPersona = useCreatePersona()
  const updatePersona = useUpdatePersona()

  const form = useForm<PersonaFormValues>({
    resolver: zodResolver(personaFormSchema) as any,
    defaultValues: {
      name: "",
      role_type: "developer",
      personality_traits: [],
      communication_style: "",
      display_order: 0,
      persona_metadata: {},
    },
  })

  useEffect(() => {
    if (persona && open) {
      form.reset({
        name: persona.name,
        role_type: persona.role_type as RoleType,
        personality_traits: persona.personality_traits || [],
        communication_style: persona.communication_style,
        display_order: persona.display_order,
        persona_metadata: persona.persona_metadata || {},
      })
    } else if (!open) {
      form.reset({
        name: "",
        role_type: "developer",
        personality_traits: [],
        communication_style: "",
        display_order: 0,
        persona_metadata: {},
      })
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
    try {
      // Ensure data is properly formatted before sending
      const payload = {
        name: data.name,
        role_type: data.role_type,
        personality_traits: data.personality_traits || [],
        communication_style: data.communication_style,
        display_order: data.display_order ?? 0,
        persona_metadata: data.persona_metadata || {},
      }

      if (isEditing) {
        await updatePersona.mutateAsync({
          personaId: persona.id,
          data: payload,
        })
      } else {
        await createPersona.mutateAsync(payload)
      }
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      // Error handled by mutation hooks
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

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
      </DialogContent>
    </Dialog>
  )
}
