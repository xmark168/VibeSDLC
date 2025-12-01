import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert"
import {
  use2FAStatus,
  useSetup2FA,
  useVerifySetup2FA,
  useRequestDisable2FA,
  useDisable2FA,
} from "@/queries/two-factor"
import { ShieldCheck, ShieldOff, Copy, Check, Loader2, AlertTriangle, Mail } from "lucide-react"
import toast from "react-hot-toast"
import { withToast } from "@/utils"

export function TwoFactorSettings() {
  const { data: status, isLoading: statusLoading } = use2FAStatus()
  const setup2FA = useSetup2FA()
  const verifySetup = useVerifySetup2FA()
  const requestDisable2FA = useRequestDisable2FA()
  const disable2FA = useDisable2FA()

  const [setupDialogOpen, setSetupDialogOpen] = useState(false)
  const [disableConfirmDialogOpen, setDisableConfirmDialogOpen] = useState(false)
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
    } catch (error) {
      toast.error("Không thể khởi tạo 2FA. Vui lòng thử lại.")
    }
  }

  const handleVerifySetup = async () => {
    try {
      const result = await verifySetup.mutateAsync({ code: verifyCode })
      setBackupCodes(result.backup_codes)
      setSetupDialogOpen(false)
      setBackupCodesDialogOpen(true)
      setVerifyCode("")
      toast.success("Đã bật xác thực hai bước!")
    } catch (error) {
      toast.error("Mã xác thực không đúng. Vui lòng thử lại.")
    }
  }

  const requiresPassword = status?.requires_password ?? true

  const handleRequestDisable = async () => {
    try {
      const result = await withToast(
        requestDisable2FA.mutateAsync({ 
          password: requiresPassword ? disablePassword : undefined 
        }),
        {
          loading: "Đang gửi mã xác thực...",
          success: "Mã xác thực đã được gửi đến email của bạn!",
          error: "Không thể gửi mã xác thực. Vui lòng thử lại.",
        }
      )
      setMaskedEmail(result.masked_email)
      setCodeExpiry(result.expires_in || 180) // 3 minutes
      setResendCooldown(30) // 30 seconds cooldown before can resend
      setDisableConfirmDialogOpen(false)
      setDisableCodeDialogOpen(true)
    } catch (error: any) {
      const errorMessage = error?.body?.detail || "Không thể gửi mã xác thực. Kiểm tra mật khẩu."
      toast.error(errorMessage)
    }
  }

  const handleResendCode = async () => {
    try {
      const result = await withToast(
        requestDisable2FA.mutateAsync({ 
          password: requiresPassword ? disablePassword : undefined 
        }),
        {
          loading: "Đang gửi lại mã xác thực...",
          success: "Mã xác thực mới đã được gửi!",
          error: "Không thể gửi lại mã. Vui lòng thử lại.",
        }
      )
      setMaskedEmail(result.masked_email)
      setCodeExpiry(result.expires_in || 180)
      setResendCooldown(30)
      setDisableCode("") // Clear old code
    } catch (error: any) {
      const errorMessage = error?.body?.detail || "Không thể gửi lại mã xác thực."
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
      toast.success("Đã tắt xác thực hai bước")
    } catch (error: any) {
      const errorMessage = error?.body?.detail || "Mã xác thực không đúng hoặc đã hết hạn."
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
    toast.success("Đã sao chép tất cả mã backup!")
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
            Xác thực hai bước (2FA)
          </CardTitle>
          <CardDescription>
            Tăng cường bảo mật tài khoản bằng ứng dụng xác thực như Google Authenticator hoặc Authy
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
                  {status?.enabled ? "Đã bật" : "Chưa bật"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {status?.enabled
                    ? "Tài khoản của bạn được bảo vệ bởi 2FA"
                    : "Bật 2FA để bảo vệ tài khoản tốt hơn"}
                </p>
              </div>
            </div>
            {status?.enabled ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setDisableConfirmDialogOpen(true)}
              >
                Tắt 2FA
              </Button>
            ) : (
              <Button onClick={handleSetup} disabled={setup2FA.isPending}>
                {setup2FA.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : null}
                Bật 2FA
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Setup Dialog */}
      <Dialog open={setupDialogOpen} onOpenChange={setSetupDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Thiết lập xác thực hai bước</DialogTitle>
            <DialogDescription>
              Quét mã QR bằng ứng dụng xác thực, sau đó nhập mã 6 chữ số để xác nhận
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
                  Hoặc nhập mã thủ công:
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
                      toast.success("Đã sao chép mã!")
                    }}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="verify-code">Mã xác thực</Label>
              <Input
                id="verify-code"
                type="text"
                inputMode="numeric"
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/[^0-9]/g, ""))}
                maxLength={6}
                className="text-center text-lg tracking-widest"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSetupDialogOpen(false)}>
              Hủy
            </Button>
            <Button
              onClick={handleVerifySetup}
              disabled={verifySetup.isPending || verifyCode.length !== 6}
            >
              {verifySetup.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : null}
              Xác nhận
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable Confirm Dialog - Step 1: Enter password (if required) and confirm */}
      <Dialog open={disableConfirmDialogOpen} onOpenChange={(open) => {
        setDisableConfirmDialogOpen(open)
        if (!open) {
          setDisablePassword("")
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Tắt xác thực hai bước</DialogTitle>
            <DialogDescription>
              {requiresPassword 
                ? "Bạn có chắc chắn muốn tắt xác thực hai bước? Nhập mật khẩu để xác nhận."
                : "Bạn có chắc chắn muốn tắt xác thực hai bước? Mã xác thực sẽ được gửi đến email của bạn."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Tắt 2FA sẽ làm giảm bảo mật tài khoản của bạn. Mã xác thực sẽ được gửi đến email của bạn.
              </AlertDescription>
            </Alert>
            {requiresPassword && (
              <div className="space-y-2">
                <Label htmlFor="disable-password">Mật khẩu</Label>
                <Input
                  id="disable-password"
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  placeholder="Nhập mật khẩu của bạn"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setDisableConfirmDialogOpen(false)
              setDisablePassword("")
            }}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={handleRequestDisable}
              disabled={requestDisable2FA.isPending || (requiresPassword && !disablePassword)}
            >
              {requestDisable2FA.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <Mail className="w-4 h-4 mr-1" />
              )}
              Gửi mã xác thực
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable Code Dialog - Step 2: Enter verification code from email */}
      <Dialog open={disableCodeDialogOpen} onOpenChange={(open) => {
        setDisableCodeDialogOpen(open)
        if (!open) {
          setDisableCode("")
          setCodeExpiry(0)
          setResendCooldown(0)
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nhập mã xác thực</DialogTitle>
            <DialogDescription>
              Mã xác thực đã được gửi đến email <span className="font-medium">{maskedEmail}</span>. Vui lòng nhập mã để hoàn tất.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant={codeExpiry > 0 ? "default" : "destructive"}>
              <Mail className="h-4 w-4" />
              <AlertDescription>
                {codeExpiry > 0 ? (
                  <>Mã xác thực hết hạn sau <span className="font-semibold">{formatTime(codeExpiry)}</span>. Kiểm tra hộp thư đến hoặc thư rác.</>
                ) : (
                  <>Mã xác thực đã hết hạn. Vui lòng gửi lại mã mới.</>
                )}
              </AlertDescription>
            </Alert>
            <div className="space-y-2">
              <Label htmlFor="disable-code">Mã xác thực</Label>
              <Input
                id="disable-code"
                type="text"
                inputMode="numeric"
                placeholder="000000"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/[^0-9]/g, ""))}
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
                  ? `Gửi lại mã sau ${resendCooldown}s` 
                  : "Gửi lại mã xác thực"}
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setDisableCodeDialogOpen(false)
              setDisableCode("")
              setCodeExpiry(0)
              setResendCooldown(0)
            }}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable}
              disabled={disable2FA.isPending || disableCode.length !== 6 || codeExpiry === 0}
            >
              {disable2FA.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : null}
              Tắt 2FA
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Backup Codes Dialog */}
      <Dialog open={backupCodesDialogOpen} onOpenChange={setBackupCodesDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Mã backup của bạn</DialogTitle>
            <DialogDescription>
              Lưu các mã này ở nơi an toàn. Mỗi mã chỉ sử dụng được một lần.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Đây là lần duy nhất bạn có thể xem các mã này. Hãy lưu lại ngay!
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
              Sao chép tất cả
            </Button>
            <Button onClick={() => setBackupCodesDialogOpen(false)}>
              Đã lưu
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
