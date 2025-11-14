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
    <div className="space-y-4">
      {label && (
        <label className="text-base font-bold text-gray-900">{label}</label>
      )}
      <div className="grid grid-cols-6 gap-3">
        {PROJECT_COLORS.map((color) => {
          const isSelected = value === color
          return (
            <button
              key={color}
              type="button"
              onClick={() => onChange(color)}
              className={cn(
                'relative h-12 w-12 rounded-xl transition-all duration-200 hover:scale-105 shadow-sm hover:shadow-md',
                isSelected && 'ring-4 ring-gray-900 ring-offset-2 scale-105 shadow-lg'
              )}
              style={{ backgroundColor: color }}
              title={color}
            >
              {isSelected && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Check className="h-6 w-6 text-white drop-shadow-xl" strokeWidth={3} />
                </div>
              )}
            </button>
          )
        })}
      </div>
      {value && (
        <div className="text-sm text-gray-600 font-mono bg-gray-100 px-3 py-2 rounded-lg inline-block">
          Selected: {value}
        </div>
      )}
    </div>
  )
}
