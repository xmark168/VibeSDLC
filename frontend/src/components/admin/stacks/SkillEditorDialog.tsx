import type { TechStack } from "@/types/stack"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { SkillFileExplorer } from "./SkillFileExplorer"

interface SkillEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stack: TechStack
}

export function SkillEditorDialog({ open, onOpenChange, stack }: SkillEditorDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-[95vw] !w-[95vw] !h-[95vh] flex flex-col p-4">
        <DialogHeader className="pb-2">
          <DialogTitle>Edit Skills: {stack.name}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden min-h-0">
          <SkillFileExplorer stackCode={stack.code} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
