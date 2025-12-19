import {
  AlertTriangle,
  Check,
  Copy,
  Loader2,
  Mail,
  ShieldCheck,
  ShieldOff,
} from "lucide-react"
import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  use2FAStatus,
  useDisable2FA,
  useRequestDisable2FA,
  useSetup2FA,
  useVerifySetup2FA,
} from "@/queries/two-factor"
import { withToast } from "@/utils"

export function TwoFactorSettings() {
  const { data: status, isLoading: statusLoading } = use2FAStatus()
  const setup2FA = useSetup2FA()
  const verifySetup = useVerifySetup2FA()
  const requestDisable2FA = useRequestDisable2FA()
  const disable2FA = useDisable2FA()

  const [setupDialogOpen, setSetupDialogOpen] = useState(false)
  const [disableConfirmDialogOpen, setDisableConfirmDialogOpen] =
    useState(false)
  const [disableCodeDialogOpen, setDisableCodeDialogOpen] = useState(false)
  const [backupCodesDialogOpen, setBackupCodesDialogOpen] = useState(false)
  const [verifyCode, setVerifyCode] = useState("")
  const [disablePassword, setDisablePassword] = useState("")
  const [disableCode, setDisableCode] = useState("")
  const [maskedEmail, setMaskedEmail] = useState("")
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [codeExpiry, setCodeExpiry] = useState(0) // Countdown for code expiry (seconds)
  const [resendCooldown, setResendCooldown] = useState(0) // Cooldown before can resend (seconds)

  // Countdown timer effect
  useEffect(() => {
    if (codeExpiry <= 0) return
    const timer = setInterval(() => {
      setCodeExpiry((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [codeExpiry])

  // Resend cooldown effect
  useEffect(() => {
    if (resendCooldown <= 0) return
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [resendCooldown])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const handleSetup = async () => {
    try {
      await setup2FA.mutateAsync()
      setSetupDialogOpen(true)
    } catch (_error) {
      toast.error("Failed to setup 2FA. Please try again.")
    }
  }

  const handleVerifySetup = async () => {
    try {
      const result = await verifySetup.mutateAsync({ code: verifyCode })
      setBackupCodes(result.backup_codes)
      setSetupDialogOpen(false)
      setBackupCodesDialogOpen(true)
      setVerifyCode("")
      toast.success("Two-factor authentication enabled!")
    } catch (_error) {
      toast.error("Invalid verification code. Please try again.")
    }
  }

  const requiresPassword = status?.requires_password ?? true

  const handleRequestDisable = async () => {
    try {
      const result = await withToast(
        requestDisable2FA.mutateAsync({
          password: requiresPassword ? disablePassword : undefined,
        }),
        {
          loading: "Sending verification code...",
          success: "Verification code sent to your email!",
          error: "Failed to send verification code. Please try again.",
        },
      )
      setMaskedEmail(result.masked_email)
      setCodeExpiry(result.expires_in || 180) // 3 minutes
      setResendCooldown(30) // 30 seconds cooldown before can resend
      setDisableConfirmDialogOpen(false)
      setDisableCodeDialogOpen(true)
    } catch (error: any) {
      const errorMessage =
        error?.body?.detail ||
        "Failed to send verification code. Check your password."
      toast.error(errorMessage)
    }
  }

  const handleResendCode = async () => {
    try {
      const result = await withToast(
        requestDisable2FA.mutateAsync({
          password: requiresPassword ? disablePassword : undefined,
        }),
        {
          loading: "Resending verification code...",
          success: "New verification code sent!",
          error: "Failed to resend code. Please try again.",
        },
      )
      setMaskedEmail(result.masked_email)
      setCodeExpiry(result.expires_in || 180)
      setResendCooldown(30)
      setDisableCode("") // Clear old code
    } catch (error: any) {
      const errorMessage =
        error?.body?.detail || "Failed to resend verification code."
      toast.error(errorMessage)
    }
  }

  const handleDisable = async () => {
    try {
      await disable2FA.mutateAsync({
        password: requiresPassword ? disablePassword : undefined,
        code: disableCode.replace(/[-\s]/g, ""),
      })
      setDisableCodeDialogOpen(false)
      setDisablePassword("")
      setDisableCode("")
      setMaskedEmail("")
      setCodeExpiry(0)
      setResendCooldown(0)
      toast.success("Two-factor authentication disabled")
    } catch (error: any) {
      const errorMessage =
        error?.body?.detail || "Invalid or expired verification code."
      toast.error(errorMessage)
    }
  }

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const copyAllBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join("\n"))
    toast.success("All backup codes copied!")
  }

  if (statusLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin" />
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5" />
            Two-Factor Authentication (2FA)
          </CardTitle>
          <CardDescription>
            Enhance account security with authenticator apps like Google
            Authenticator or Authy
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-3">
              {status?.enabled ? (
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                  <ShieldCheck className="w-5 h-5 text-green-600" />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
                  <ShieldOff className="w-5 h-5 text-yellow-600" />
                </div>
              )}
              <div>
                <p className="font-medium">
                  {status?.enabled ? "Enabled" : "Disabled"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {status?.enabled
                    ? "Your account is protected by 2FA"
                    : "Enable 2FA for better account protection"}
                </p>
              </div>
            </div>
            {status?.enabled ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setDisableConfirmDialogOpen(true)}
              >
                Disable 2FA
              </Button>
            ) : (
              <Button onClick={handleSetup} disabled={setup2FA.isPending}>
                {setup2FA.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : null}
                Enable 2FA
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Setup Dialog */}
      <Dialog open={setupDialogOpen} onOpenChange={setSetupDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Setup Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Scan the QR code with your authenticator app, then enter the
              6-digit code to confirm
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {setup2FA.data?.qr_code_uri && (
              <div className="flex justify-center p-4 bg-white rounded-lg">
                <img
                  src={setup2FA.data.qr_code_uri}
                  alt="QR Code"
                  className="w-48 h-48"
                />
              </div>
            )}
            {setup2FA.data?.secret && (
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">
                  Or enter code manually:
                </Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-muted rounded text-sm font-mono break-all">
                    {setup2FA.data.secret}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      navigator.clipboard.writeText(setup2FA.data?.secret || "")
                      toast.success("Code copied!")
                    }}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="verify-code">Verification code</Label>
              <Input
                id="verify-code"
                type="text"
                inputMode="numeric"
                placeholder="000000"
                value={verifyCode}
                onChange={(e) =>
                  setVerifyCode(e.target.value.replace(/[^0-9]/g, ""))
                }
                maxLength={6}
                className="text-center text-lg tracking-widest"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSetupDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleVerifySetup}
              disabled={verifySetup.isPending || verifyCode.length !== 6}
            >
              {verifySetup.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : null}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable Confirm Dialog - Step 1: Enter password (if required) and confirm */}
      <Dialog
        open={disableConfirmDialogOpen}
        onOpenChange={(open) => {
          setDisableConfirmDialogOpen(open)
          if (!open) {
            setDisablePassword("")
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              {requiresPassword
                ? "Are you sure you want to disable 2FA? Enter your password to confirm."
                : "Are you sure you want to disable 2FA? A verification code will be sent to your email."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Disabling 2FA will reduce your account security. A verification
                code will be sent to your email.
              </AlertDescription>
            </Alert>
            {requiresPassword && (
              <div className="space-y-2">
                <Label htmlFor="disable-password">Password</Label>
                <Input
                  id="disable-password"
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  placeholder="Enter your password"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDisableConfirmDialogOpen(false)
                setDisablePassword("")
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRequestDisable}
              disabled={
                requestDisable2FA.isPending ||
                (requiresPassword && !disablePassword)
              }
            >
              {requestDisable2FA.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <Mail className="w-4 h-4 mr-1" />
              )}
              Send verification code
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable Code Dialog - Step 2: Enter verification code from email */}
      <Dialog
        open={disableCodeDialogOpen}
        onOpenChange={(open) => {
          setDisableCodeDialogOpen(open)
          if (!open) {
            setDisableCode("")
            setCodeExpiry(0)
            setResendCooldown(0)
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Enter Verification Code</DialogTitle>
            <DialogDescription>
              Verification code sent to{" "}
              <span className="font-medium">{maskedEmail}</span>. Please enter
              the code to complete.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant={codeExpiry > 0 ? "default" : "destructive"}>
              <Mail className="h-4 w-4" />
              <AlertDescription>
                {codeExpiry > 0 ? (
                  <>
                    Code expires in{" "}
                    <span className="font-semibold">
                      {formatTime(codeExpiry)}
                    </span>
                    . Check your inbox or spam folder.
                  </>
                ) : (
                  <>Verification code expired. Please resend a new code.</>
                )}
              </AlertDescription>
            </Alert>
            <div className="space-y-2">
              <Label htmlFor="disable-code">Verification code</Label>
              <Input
                id="disable-code"
                type="text"
                inputMode="numeric"
                placeholder="000000"
                value={disableCode}
                onChange={(e) =>
                  setDisableCode(e.target.value.replace(/[^0-9]/g, ""))
                }
                maxLength={6}
                className="text-center text-lg tracking-widest"
                disabled={codeExpiry === 0}
              />
            </div>
            {/* Resend button */}
            <div className="flex justify-center">
              <Button
                variant="link"
                size="sm"
                onClick={handleResendCode}
                disabled={resendCooldown > 0 || requestDisable2FA.isPending}
                className="text-muted-foreground"
              >
                {requestDisable2FA.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : null}
                {resendCooldown > 0
                  ? `Resend code in ${resendCooldown}s`
                  : "Resend verification code"}
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDisableCodeDialogOpen(false)
                setDisableCode("")
                setCodeExpiry(0)
                setResendCooldown(0)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable}
              disabled={
                disable2FA.isPending ||
                disableCode.length !== 6 ||
                codeExpiry === 0
              }
            >
              {disable2FA.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : null}
              Disable 2FA
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Backup Codes Dialog */}
      <Dialog
        open={backupCodesDialogOpen}
        onOpenChange={setBackupCodesDialogOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Your Backup Codes</DialogTitle>
            <DialogDescription>
              Save these codes in a secure place. Each code can only be used
              once.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This is the only time you can view these codes. Save them now!
              </AlertDescription>
            </Alert>
            <div className="grid grid-cols-2 gap-2">
              {backupCodes.map((code, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-muted rounded font-mono text-sm"
                >
                  <span>{code}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => copyToClipboard(code, index)}
                  >
                    {copiedIndex === index ? (
                      <Check className="w-3 h-3 text-green-500" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={copyAllBackupCodes}>
              <Copy className="w-4 h-4 mr-1" />
              Copy all
            </Button>
            <Button onClick={() => setBackupCodesDialogOpen(false)}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
