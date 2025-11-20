import { Loader2, Rocket, Sparkles } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface WelcomeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSendMessage: (content: string) => boolean
  isConnected: boolean // This receives isReady value from parent
}

export function WelcomeDialog({
  open,
  onOpenChange,
  onSendMessage,
  isConnected,
}: WelcomeDialogProps) {
  const [isStarting, setIsStarting] = useState(false)

  const handleStart = () => {
    if (!isConnected) {
      console.warn("WebSocket not connected yet")
      return
    }

    setIsStarting(true)

    // Send message immediately
    const success = onSendMessage("Bắt đầu")
    console.log("Message sent:", success)

    // Close dialog
    onOpenChange(false)
    setIsStarting(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" showCloseButton={false}>
        <DialogHeader className="text-center items-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <DialogTitle className="text-2xl font-bold">
            Chào mừng đến với không gian làm việc
          </DialogTitle>
          <DialogDescription className="text-center text-base">
            Bắt đầu cuộc trò chuyện với AI Agent để tạo dự án.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="flex flex-col items-center gap-2 sm:justify-center mt-4">
          <Button
            onClick={handleStart}
            disabled={isStarting || !isConnected}
            className="w-full sm:w-auto bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold px-8 py-6 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {!isConnected ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Đang kết nối...
              </>
            ) : isStarting ? (
              <>
                <Rocket className="w-5 h-5 mr-2 animate-bounce" />
                Đang khởi động...
              </>
            ) : (
              <>
                <Rocket className="w-5 h-5 mr-2" />
                Bắt đầu
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
