import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { TechStack } from "@/types/stack"
import { BoilerplateFileExplorer } from "./BoilerplateFileExplorer"

interface BoilerplateEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stack: TechStack
}

export function BoilerplateEditorDialog({
  open,
  onOpenChange,
  stack,
}: BoilerplateEditorDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-[95vw] !w-[95vw] !h-[95vh] flex flex-col p-4">
        <DialogHeader className="pb-2">
          <DialogTitle>Edit Boilerplate: {stack.name}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden min-h-0">
          <BoilerplateFileExplorer stackCode={stack.code} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
