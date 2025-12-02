import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import type { UserAdmin, UserAdminCreate } from "@/types/user"
import { useCreateUser, useUpdateUser } from "@/queries/users"
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
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Loader2 } from "lucide-react"

const userFormSchema = z.object({
  username: z.string().max(50).optional().nullable(),
  full_name: z.string().max(50).optional().nullable(),
  email: z.string().email("Invalid email address"),
  password: z.string().optional().or(z.literal("")),
  role: z.enum(["admin", "user"]),
  is_active: z.boolean(),
})

type UserFormValues = z.infer<typeof userFormSchema>

interface UserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user?: UserAdmin
  onSuccess?: () => void
}

export function UserDialog({ open, onOpenChange, user, onSuccess }: UserDialogProps) {
  const isEditing = !!user
  const createUser = useCreateUser()
  const updateUser = useUpdateUser()

  const form = useForm<UserFormValues>({
    resolver: zodResolver(userFormSchema),
    defaultValues: {
      username: "",
      full_name: "",
      email: "",
      password: "",
      role: "user",
      is_active: true,
    },
  })

  useEffect(() => {
    if (user) {
      form.reset({
        username: user.username || "",
        full_name: user.full_name || "",
        email: user.email,
        password: "",
        role: user.role,
        is_active: user.is_active,
      })
    } else {
      form.reset({
        username: "",
        full_name: "",
        email: "",
        password: "",
        role: "user",
        is_active: true,
      })
    }
  }, [user, form, open])

  const onSubmit = async (data: UserFormValues) => {
    try {
      // Validate password for new users
      if (!isEditing && (!data.password || data.password.length < 6)) {
        form.setError("password", { message: "Password must be at least 6 characters" })
        return
      }

      if (isEditing && user) {
        const updateData: Record<string, unknown> = {
          username: data.username || null,
          full_name: data.full_name || null,
          email: data.email,
          role: data.role,
          is_active: data.is_active,
        }
        if (data.password && data.password.length > 0) {
          if (data.password.length < 6) {
            form.setError("password", { message: "Password must be at least 6 characters" })
            return
          }
          updateData.password = data.password
        }
        await updateUser.mutateAsync({ userId: user.id, data: updateData })
      } else {
        const createData: UserAdminCreate = {
          username: data.username || null,
          full_name: data.full_name || null,
          email: data.email,
          password: data.password!,
          role: data.role,
          is_active: data.is_active,
        }
        await createUser.mutateAsync(createData)
      }

      form.reset()
      onSuccess?.()
    } catch (error) {
      console.error("Form submission error:", error)
    }
  }

  const isLoading = createUser.isPending || updateUser.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Edit User" : "Create New User"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the user details below."
              : "Fill in the details to create a new user account."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        value={field.value || ""}
                        placeholder="johndoe"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Full Name</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        value={field.value || ""}
                        placeholder="John Doe"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      placeholder="john@example.com"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{isEditing ? "New Password" : "Password *"}</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="password"
                      placeholder={isEditing ? "Leave empty to keep current" : "Enter password"}
                    />
                  </FormControl>
                  {isEditing && (
                    <FormDescription>
                      Leave empty to keep the current password
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                    <div className="space-y-0.5">
                      <FormLabel className="text-sm">Active</FormLabel>
                      <FormDescription className="text-xs">
                        Account status
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isEditing ? "Update User" : "Create User"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
