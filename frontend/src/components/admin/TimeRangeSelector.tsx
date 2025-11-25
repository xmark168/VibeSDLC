import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { TimeRange } from "@/types"

interface TimeRangeSelectorProps {
  value: TimeRange
  onChange: (value: TimeRange) => void
  className?: string
}

const timeRangeOptions: { value: TimeRange; label: string }[] = [
  { value: "1h", label: "1H" },
  { value: "6h", label: "6H" },
  { value: "24h", label: "24H" },
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
]

export function TimeRangeSelector({ value, onChange, className }: TimeRangeSelectorProps) {
  return (
    <div className={cn("inline-flex rounded-md shadow-sm", className)}>
      {timeRangeOptions.map((option, index) => (
        <Button
          key={option.value}
          variant={value === option.value ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-none",
            index === 0 && "rounded-l-md",
            index === timeRangeOptions.length - 1 && "rounded-r-md",
            value === option.value && "z-10"
          )}
        >
          {option.label}
        </Button>
      ))}
    </div>
  )
}
