import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { Plus, Trash2, Save } from "lucide-react"
import type { TechStack, TechStackCreate, TechStackUpdate } from "@/types/stack"
import { useCreateStack, useUpdateStack } from "@/queries/stacks"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface StackDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stack?: TechStack
  onSuccess?: () => void
}

interface StackFormValues {
  code: string
  name: string
  description: string
  image: string
  display_order: number
  is_active: boolean
}

export function StackDialog({ open, onOpenChange, stack, onSuccess }: StackDialogProps) {
  const isEditing = !!stack
  const [stackConfig, setStackConfig] = useState<Record<string, string>>({})
  const [newKey, setNewKey] = useState("")
  const [newValue, setNewValue] = useState("")

  const createStack = useCreateStack()
  const updateStack = useUpdateStack()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<StackFormValues>({
    defaultValues: {
      code: "",
      name: "",
      description: "",
      image: "",
      display_order: 0,
      is_active: true,
    },
  })

  useEffect(() => {
    if (stack) {
      reset({
        code: stack.code,
        name: stack.name,
        description: stack.description || "",
        image: stack.image || "",
        display_order: stack.display_order,
        is_active: stack.is_active,
      })
      setStackConfig(stack.stack_config || {})
    } else {
      reset({
        code: "",
        name: "",
        description: "",
        image: "",
        display_order: 0,
        is_active: true,
      })
      setStackConfig({})
    }
  }, [stack, reset, open])

  const handleAddConfigItem = () => {
    if (newKey.trim() && newValue.trim()) {
      setStackConfig((prev) => ({
        ...prev,
        [newKey.trim()]: newValue.trim(),
      }))
      setNewKey("")
      setNewValue("")
    }
  }

  const handleRemoveConfigItem = (key: string) => {
    setStackConfig((prev) => {
      const updated = { ...prev }
      delete updated[key]
      return updated
    })
  }

  const onSubmit = async (data: StackFormValues) => {
    try {
      const payload = {
        ...data,
        stack_config: stackConfig,
      }

      if (isEditing) {
        await updateStack.mutateAsync({
          stackId: stack.id,
          data: payload as TechStackUpdate,
        })
      } else {
        await createStack.mutateAsync(payload as TechStackCreate)
      }
      onSuccess?.()
    } catch (error) {
      // Error handled by mutation hooks
    }
  }

  const isPending = createStack.isPending || updateStack.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? `Edit Stack: ${stack.name}` : "Create New Stack"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="code">Code</Label>
                  <Input
                    id="code"
                    {...register("code", { required: "Code is required" })}
                    placeholder="nextjs"
                    disabled={isEditing}
                  />
                  {errors.code && (
                    <p className="text-xs text-destructive">{errors.code.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    {...register("name", { required: "Name is required" })}
                    placeholder="Next.js Full Stack"
                  />
                  {errors.name && (
                    <p className="text-xs text-destructive">{errors.name.message}</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  {...register("description")}
                  placeholder="A modern full-stack framework..."
                  className="resize-none"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="image">Image URL</Label>
                  <Input
                    id="image"
                    {...register("image")}
                    placeholder="https://example.com/image.png"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="display_order">Display Order</Label>
                  <Input
                    id="display_order"
                    type="number"
                    {...register("display_order", { valueAsNumber: true })}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Switch
                  id="is_active"
                  checked={watch("is_active")}
                  onCheckedChange={(checked) => setValue("is_active", checked)}
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
            </CardContent>
          </Card>

          {/* Stack Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Stack Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Existing config items */}
              <div className="space-y-2">
                {Object.entries(stackConfig).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Input
                      value={key}
                      disabled
                      className="flex-1"
                    />
                    <Input
                      value={value}
                      onChange={(e) =>
                        setStackConfig((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveConfigItem(key)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Add new config item */}
              <div className="flex items-center gap-2 pt-2 border-t">
                <Input
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="Key (e.g., runtime)"
                  className="flex-1"
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddConfigItem())}
                />
                <Input
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="Value (e.g., bun)"
                  className="flex-1"
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddConfigItem())}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleAddConfigItem}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Submit Button */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              <Save className="w-4 h-4 mr-2" />
              {isPending ? "Saving..." : isEditing ? "Update Stack" : "Create Stack"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
