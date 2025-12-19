import { Check, Eye, EyeOff, Key, Loader2, Lock, X } from "lucide-react"
import { useState } from "react"
import toast from "react-hot-toast"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  useChangePassword,
  usePasswordStatus,
  useSetPassword,
} from "@/queries/profile"

export function PasswordSettings() {
  const { data: passwordStatus, isLoading: statusLoading } = usePasswordStatus()
  const changePasswordMutation = useChangePassword()
  const setPasswordMutation = useSetPassword()

  const [isEditing, setIsEditing] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const hasPassword = passwordStatus?.has_password ?? false
  const isSubmitting =
    changePasswordMutation.isPending || setPasswordMutation.isPending

  const passwordRequirements = [
    { label: "At least 8 characters", met: newPassword.length >= 8 },
    { label: "Contains letters", met: /[a-zA-Z]/.test(newPassword) },
    { label: "Contains numbers", met: /[0-9]/.test(newPassword) },
  ]

  const allRequirementsMet = passwordRequirements.every((r) => r.met)
  const passwordsMatch =
    newPassword === confirmPassword && confirmPassword !== ""

  const resetForm = () => {
    setCurrentPassword("")
    setNewPassword("")
    setConfirmPassword("")
    setIsEditing(false)
    setShowCurrentPassword(false)
    setShowNewPassword(false)
    setShowConfirmPassword(false)
  }

  const handleSubmit = async () => {
    if (!allRequirementsMet) {
      toast.error("Password does not meet requirements")
      return
    }

    if (!passwordsMatch) {
      toast.error("Passwords do not match")
      return
    }

    try {
      if (hasPassword) {
        if (!currentPassword) {
          toast.error("Please enter current password")
          return
        }
        await changePasswordMutation.mutateAsync({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        })
        toast.success("Password changed successfully")
      } else {
        await setPasswordMutation.mutateAsync({
          new_password: newPassword,
          confirm_password: confirmPassword,
        })
        toast.success("Password created successfully")
      }
      resetForm()
    } catch (error: any) {
      toast.error(error?.body?.detail || error?.message || "An error occurred")
    }
  }

  if (statusLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Password
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          Password
        </CardTitle>
        <CardDescription>
          {hasPassword
            ? "Change your login password"
            : "Create a password to login with email"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!isEditing ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-secondary rounded-lg">
                <Lock className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium">
                  {hasPassword ? "Password is set" : "No password set"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {hasPassword
                    ? "You can login with email and password"
                    : passwordStatus?.login_provider
                      ? `You are logged in via ${passwordStatus.login_provider}`
                      : "Create a password for another login method"}
                </p>
              </div>
            </div>
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              {hasPassword ? "Change password" : "Create password"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {hasPassword && (
              <div className="space-y-2">
                <Label htmlFor="current-password">Current password</Label>
                <div className="relative">
                  <Input
                    id="current-password"
                    type={showCurrentPassword ? "text" : "password"}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="pr-10"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showCurrentPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="new-password">New password</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="pr-10"
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showNewPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {newPassword && (
                <div className="space-y-1 pt-1">
                  {passwordRequirements.map((req, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 text-sm"
                    >
                      {req.met ? (
                        <Check className="h-3.5 w-3.5 text-green-500" />
                      ) : (
                        <X className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                      <span
                        className={
                          req.met ? "text-green-500" : "text-muted-foreground"
                        }
                      >
                        {req.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm password</Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  className={`pr-10 ${
                    confirmPassword && !passwordsMatch ? "border-red-500" : ""
                  } ${passwordsMatch ? "border-green-500" : ""}`}
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {confirmPassword && !passwordsMatch && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <X className="h-3.5 w-3.5" />
                  Passwords do not match
                </p>
              )}
              {passwordsMatch && (
                <p className="text-sm text-green-500 flex items-center gap-1">
                  <Check className="h-3.5 w-3.5" />
                  Passwords match
                </p>
              )}
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={resetForm}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={
                  !allRequirementsMet || !passwordsMatch || isSubmitting
                }
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : hasPassword ? (
                  "Change password"
                ) : (
                  "Create password"
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
