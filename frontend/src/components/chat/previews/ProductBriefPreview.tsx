import { AlertTriangle } from "lucide-react"

interface ProductBriefPreviewProps {
  brief: any
  incompleteFlag?: boolean
}

export function ProductBriefPreview({
  brief,
  incompleteFlag,
}: ProductBriefPreviewProps) {
  if (!brief) return null

  const {
    product_summary,
    problem_statement,
    target_users,
    product_goals,
    scope,
  } = brief

  return (
    <div className="space-y-4 max-h-[400px] overflow-y-auto">
      {incompleteFlag && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-700 dark:text-yellow-300">
            <strong>Lưu ý:</strong> PRD chưa hoàn chỉnh. Một số thông tin có
            thể được suy luận hoặc còn thiếu.
          </div>
        </div>
      )}

      {product_summary && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Tóm tắt sản phẩm:
          </h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {product_summary}
          </p>
        </div>
      )}

      {problem_statement && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Vấn đề cần giải quyết:
          </h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {problem_statement}
          </p>
        </div>
      )}

      {target_users && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Đối tượng người dùng:
          </h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {target_users}
          </p>
        </div>
      )}

      {product_goals && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Mục tiêu sản phẩm:
          </h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {product_goals}
          </p>
        </div>
      )}

      {scope && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Phạm vi:
          </h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {scope}
          </p>
        </div>
      )}
    </div>
  )
}
