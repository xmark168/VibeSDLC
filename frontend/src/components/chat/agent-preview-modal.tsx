import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { CheckCircle, Edit, RefreshCw } from 'lucide-react'
import type { AgentPreview } from '@/hooks/useChatWebSocket'
import { ProductBriefPreview, ProductVisionPreview, BacklogPreview, SprintPlanPreview } from './previews'

interface AgentPreviewModalProps {
  preview: AgentPreview | null
  onSubmit: (preview_id: string, choice: string, edit_changes?: string) => void
}

export function AgentPreviewModal({ preview, onSubmit }: AgentPreviewModalProps) {
  const [editMode, setEditMode] = useState(false)
  const [editChanges, setEditChanges] = useState('')

  if (!preview) return null

  const handleApprove = () => {
    onSubmit(preview.preview_id, 'approve')
  }

  const handleEdit = () => {
    setEditMode(true)
  }

  const handleSubmitEdit = () => {
    if (!editChanges.trim()) {
      // If no changes provided, just cancel
      setEditMode(false)
      return
    }
    onSubmit(preview.preview_id, 'edit', editChanges)
    setEditMode(false)
    setEditChanges('')
  }

  const handleRegenerate = () => {
    onSubmit(preview.preview_id, 'regenerate')
  }

  const handleCancelEdit = () => {
    setEditMode(false)
    setEditChanges('')
  }

  const renderContent = () => {
    // Route based on preview_type
    switch (preview.preview_type) {
      case 'product_brief':
        return (
          <ProductBriefPreview
            brief={preview.brief}
            incompleteFlag={preview.incomplete_flag}
          />
        )
      case 'product_vision':
        return (
          <ProductVisionPreview
            vision={preview.vision}
            qualityScore={preview.quality_score}
            validationResult={preview.validation_result}
          />
        )
      case 'product_backlog':
        return (
          <BacklogPreview
            backlog={preview.backlog}
          />
        )
      case 'sprint_plan':
        return (
          <SprintPlanPreview
            sprintPlan={preview.sprint_plan}
          />
        )
      default:
        // Fallback: try to render whatever is available
        if (preview.vision) {
          return (
            <ProductVisionPreview
              vision={preview.vision}
              qualityScore={preview.quality_score}
              validationResult={preview.validation_result}
            />
          )
        } else if (preview.brief) {
          return (
            <ProductBriefPreview
              brief={preview.brief}
              incompleteFlag={preview.incomplete_flag}
            />
          )
        } else if (preview.backlog) {
          return (
            <BacklogPreview
              backlog={preview.backlog}
            />
          )
        } else if (preview.sprint_plan) {
          return (
            <SprintPlanPreview
              sprintPlan={preview.sprint_plan}
            />
          )
        }
        return <div className="text-sm text-muted-foreground">No preview data available</div>
    }
  }

  return (
    <Dialog open={!!preview} modal>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>{preview.title}</span>
          </DialogTitle>
          <DialogDescription>
            {preview.prompt}
          </DialogDescription>
        </DialogHeader>

        {!editMode ? (
          <>
            <div className="overflow-y-auto flex-1 -mx-6 px-6">
              {renderContent()}
            </div>
            <DialogFooter className="flex gap-2 flex-shrink-0">
              {preview.options.includes('regenerate') && (
                <Button
                  variant="outline"
                  onClick={handleRegenerate}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Tạo lại
                </Button>
              )}
              {preview.options.includes('edit') && (
                <Button
                  variant="outline"
                  onClick={handleEdit}
                  className="flex items-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  Chỉnh sửa
                </Button>
              )}
              {preview.options.includes('approve') && (
                <Button
                  onClick={handleApprove}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle className="w-4 h-4" />
                  Phê duyệt
                </Button>
              )}
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="overflow-y-auto flex-1 -mx-6 px-6">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-foreground mb-2 block">
                    Nhập các thay đổi bạn muốn áp dụng:
                  </label>
                  <Textarea
                    value={editChanges}
                    onChange={(e) => setEditChanges(e.target.value)}
                    placeholder="Ví dụ: Thay đổi tên sản phẩm thành 'TaskMaster Pro Plus', thêm tính năng AI chatbot..."
                    className="min-h-[120px] p-3 focus-visible:ring-0 focus-visible:ring-offset-0"
                    autoFocus
                  />
                </div>
              </div>
            </div>
            <DialogFooter className="flex gap-2 flex-shrink-0">
              <Button
                variant="outline"
                onClick={handleCancelEdit}
              >
                Hủy
              </Button>
              <Button
                onClick={handleSubmitEdit}
                disabled={!editChanges.trim()}
              >
                Áp dụng thay đổi
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
