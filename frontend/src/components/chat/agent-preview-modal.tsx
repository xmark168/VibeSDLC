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
import { CheckCircle, Edit, RefreshCw, AlertTriangle } from 'lucide-react'
import type { AgentPreview } from '@/hooks/useChatWebSocket'

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

  const renderBriefContent = () => {
    if (!preview.brief) return null

    const { product_name, description, target_audience, key_features, benefits, competitors, completeness_note } = preview.brief

    return (
      <div className="space-y-4 max-h-[400px] overflow-y-auto">
        {preview.incomplete_flag && (
          <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-700 dark:text-yellow-300">
              <strong>Lưu ý:</strong> Brief chưa hoàn chỉnh. Một số thông tin có thể được suy luận hoặc còn thiếu.
            </div>
          </div>
        )}

        {product_name && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Tên sản phẩm:</h4>
            <p className="text-sm text-muted-foreground">{product_name}</p>
          </div>
        )}

        {description && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Mô tả:</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{description}</p>
          </div>
        )}

        {target_audience && target_audience.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Đối tượng mục tiêu:</h4>
            <ul className="list-disc list-inside space-y-1">
              {target_audience.map((audience: string, idx: number) => (
                <li key={idx} className="text-sm text-muted-foreground">{audience}</li>
              ))}
            </ul>
          </div>
        )}

        {key_features && key_features.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Tính năng chính:</h4>
            <ul className="list-disc list-inside space-y-1">
              {key_features.map((feature: string, idx: number) => (
                <li key={idx} className="text-sm text-muted-foreground">{feature}</li>
              ))}
            </ul>
          </div>
        )}

        {benefits && benefits.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Lợi ích:</h4>
            <ul className="list-disc list-inside space-y-1">
              {benefits.map((benefit: string, idx: number) => (
                <li key={idx} className="text-sm text-muted-foreground">{benefit}</li>
              ))}
            </ul>
          </div>
        )}

        {competitors && competitors.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Đối thủ cạnh tranh:</h4>
            <ul className="list-disc list-inside space-y-1">
              {competitors.map((competitor: string, idx: number) => (
                <li key={idx} className="text-sm text-muted-foreground">{competitor}</li>
              ))}
            </ul>
          </div>
        )}

        {completeness_note && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">Ghi chú:</h4>
            <p className="text-sm text-muted-foreground italic">{completeness_note}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <Dialog open={!!preview} modal>
      <DialogContent className="max-w-3xl">
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
            {renderBriefContent()}
            <DialogFooter className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleRegenerate}
                className="flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Tạo lại
              </Button>
              <Button
                variant="outline"
                onClick={handleEdit}
                className="flex items-center gap-2"
              >
                <Edit className="w-4 h-4" />
                Chỉnh sửa
              </Button>
              <Button
                onClick={handleApprove}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
              >
                <CheckCircle className="w-4 h-4" />
                Phê duyệt
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground mb-2 block">
                  Nhập các thay đổi bạn muốn áp dụng:
                </label>
                <Textarea
                  value={editChanges}
                  onChange={(e) => setEditChanges(e.target.value)}
                  placeholder="Ví dụ: Thay đổi tên sản phẩm thành 'TaskMaster Pro Plus', thêm tính năng AI chatbot..."
                  className="min-h-[120px]"
                  autoFocus
                />
              </div>
            </div>
            <DialogFooter className="flex gap-2">
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
