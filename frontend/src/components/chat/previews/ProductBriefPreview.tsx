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
    product_name,
    description,
    target_audience,
    key_features,
    benefits,
    competitors,
    completeness_note,
  } = brief

  return (
    <div className="space-y-4 max-h-[400px] overflow-y-auto">
      {incompleteFlag && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-700 dark:text-yellow-300">
            <strong>Lưu ý:</strong> Brief chưa hoàn chỉnh. Một số thông tin có
            thể được suy luận hoặc còn thiếu.
          </div>
        </div>
      )}

      {product_name && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Tên sản phẩm:
          </h4>
          <p className="text-sm text-muted-foreground">{product_name}</p>
        </div>
      )}

      {description && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">Mô tả:</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {description}
          </p>
        </div>
      )}

      {target_audience && target_audience.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Đối tượng mục tiêu:
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {target_audience.map((audience: string, idx: number) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {audience}
              </li>
            ))}
          </ul>
        </div>
      )}

      {key_features && key_features.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Tính năng chính:
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {key_features.map((feature: string, idx: number) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {feature}
              </li>
            ))}
          </ul>
        </div>
      )}

      {benefits && benefits.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Lợi ích:
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {benefits.map((benefit: string, idx: number) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {benefit}
              </li>
            ))}
          </ul>
        </div>
      )}

      {competitors && competitors.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Đối thủ cạnh tranh:
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {competitors.map((competitor: string, idx: number) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {competitor}
              </li>
            ))}
          </ul>
        </div>
      )}

      {completeness_note && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            Ghi chú:
          </h4>
          <p className="text-sm text-muted-foreground italic">
            {completeness_note}
          </p>
        </div>
      )}
    </div>
  )
}
