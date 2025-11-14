import { Check } from 'lucide-react'
import { PROJECT_COLORS } from '@/features/projects/types'
import { cn } from '@/lib/utils'

interface ColorPickerProps {
  value: string | null
  onChange: (color: string) => void
  label?: string
}

export const ColorPicker = ({ value, onChange, label = 'Project Color' }: ColorPickerProps) => {
  return (
    <div className="space-y-3">
      {label && <label className="text-sm font-semibold text-foreground">{label}</label>}
      <div className="grid grid-cols-6 gap-3">
        {PROJECT_COLORS.map((color) => {
          const isSelected = value === color
          return (
            <button
              key={color}
              type="button"
              onClick={() => onChange(color)}
              className={cn(
                'relative h-10 w-10 rounded-xl transition-all duration-300 hover:scale-110 hover:shadow-lg',
                isSelected && 'ring-2 ring-offset-2 ring-foreground scale-110 shadow-xl'
              )}
              style={{ backgroundColor: color }}
              title={color}
            >
              {isSelected && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Check className="h-5 w-5 text-white drop-shadow-lg" strokeWidth={3} />
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
