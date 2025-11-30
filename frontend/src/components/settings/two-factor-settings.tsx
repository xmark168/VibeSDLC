import { useState } from "react"
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
  useDisable2FA,
  useRegenerateBackupCodes,
} from "@/queries/two-factor"
import { ShieldCheck, ShieldOff, Copy, Check, RefreshCw, Loader2, AlertTriangle } from "lucide-react"
import toast from "react-hot-toast"

export function TwoFactorSettings() {
  const { data: status, isLoading: statusLoading } = use2FAStatus()
  const setup2FA = useSetup2FA()
  const verifySetup = useVerifySetup2FA()
  const disable2FA = useDisable2FA()
  const regenerateBackupCodes = useRegenerateBackupCodes()

  const [setupDialogOpen, setSetupDialogOpen] = useState(false)
  const [disableDialogOpen, setDisableDialogOpen] = useState(false)
  const [backupCodesDialogOpen, setBackupCodesDialogOpen] = useState(false)
  const [verifyCode, setVerifyCode] = useState("")
  const [disablePassword, setDisablePassword] = useState("")
  const [disableCode, setDisableCode] = useState("")
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

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

  const handleDisable = async () => {
    try {
      await disable2FA.mutateAsync({
        password: disablePassword,
        code: disableCode.replace(/[-\s]/g, ""),
      })
      setDisableDialogOpen(false)
      setDisablePassword("")
      setDisableCode("")
      toast.success("Đã tắt xác thực hai bước")
    } catch (error) {
      toast.error("Không thể tắt 2FA. Kiểm tra mật khẩu và mã xác thực.")
    }
  }

  const handleRegenerateBackupCodes = async () => {
    try {
      const result = await regenerateBackupCodes.mutateAsync()
      setBackupCodes(result.backup_codes)
      setBackupCodesDialogOpen(true)
      toast.success("Đã tạo mã backup mới!")
    } catch (error) {
      toast.error("Không thể tạo mã backup mới.")
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
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRegenerateBackupCodes}
                  disabled={regenerateBackupCodes.isPending}
                >
                  {regenerateBackupCodes.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  ) : (
                    <RefreshCw className="w-4 h-4 mr-1" />
                  )}
                  Tạo mã backup mới
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setDisableDialogOpen(true)}
                >
                  Tắt 2FA
                </Button>
              </div>
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

      {/* Disable Dialog */}
      <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Tắt xác thực hai bước</DialogTitle>
            <DialogDescription>
              Nhập mật khẩu và mã xác thực để tắt 2FA
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Tắt 2FA sẽ làm giảm bảo mật tài khoản của bạn
              </AlertDescription>
            </Alert>
            <div className="space-y-2">
              <Label htmlFor="disable-password">Mật khẩu</Label>
              <Input
                id="disable-password"
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="disable-code">Mã xác thực hoặc mã backup</Label>
              <Input
                id="disable-code"
                type="text"
                placeholder="000000 hoặc XXXX-XXXX"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisableDialogOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable}
              disabled={disable2FA.isPending || !disablePassword || !disableCode}
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
