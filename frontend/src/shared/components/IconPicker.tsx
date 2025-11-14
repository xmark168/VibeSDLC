import { useState } from 'react'
import {
  FolderKanban,
  Rocket,
  Code,
  Database,
  Cloud,
  Cpu,
  Globe,
  Smartphone,
  Layout,
  Zap,
  Heart,
  Star,
  Sun,
  Moon,
  Coffee,
  Music,
  Camera,
  Book,
  Briefcase,
  Target,
  TrendingUp,
  Package,
  Shield,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input.jsx'

// Available icons
const AVAILABLE_ICONS = [
  { name: 'folder-kanban', Icon: FolderKanban, label: 'Kanban' },
  { name: 'rocket', Icon: Rocket, label: 'Rocket' },
  { name: 'code', Icon: Code, label: 'Code' },
  { name: 'database', Icon: Database, label: 'Database' },
  { name: 'cloud', Icon: Cloud, label: 'Cloud' },
  { name: 'cpu', Icon: Cpu, label: 'CPU' },
  { name: 'globe', Icon: Globe, label: 'Globe' },
  { name: 'smartphone', Icon: Smartphone, label: 'Mobile' },
  { name: 'layout', Icon: Layout, label: 'Layout' },
  { name: 'zap', Icon: Zap, label: 'Zap' },
  { name: 'heart', Icon: Heart, label: 'Heart' },
  { name: 'star', Icon: Star, label: 'Star' },
  { name: 'sun', Icon: Sun, label: 'Sun' },
  { name: 'moon', Icon: Moon, label: 'Moon' },
  { name: 'coffee', Icon: Coffee, label: 'Coffee' },
  { name: 'music', Icon: Music, label: 'Music' },
  { name: 'camera', Icon: Camera, label: 'Camera' },
  { name: 'book', Icon: Book, label: 'Book' },
  { name: 'briefcase', Icon: Briefcase, label: 'Briefcase' },
  { name: 'target', Icon: Target, label: 'Target' },
  { name: 'trending-up', Icon: TrendingUp, label: 'Trending' },
  { name: 'package', Icon: Package, label: 'Package' },
  { name: 'shield', Icon: Shield, label: 'Shield' },
  { name: 'users', Icon: Users, label: 'Users' },
]

interface IconPickerProps {
  value: string | null
  onChange: (icon: string) => void
  label?: string
}

export const IconPicker = ({ value, onChange, label = 'Project Icon' }: IconPickerProps) => {
  const [search, setSearch] = useState('')

  const filteredIcons = AVAILABLE_ICONS.filter(
    (icon) =>
      icon.name.toLowerCase().includes(search.toLowerCase()) ||
      icon.label.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-4">
      {label && (
        <label className="text-base font-bold text-gray-900">{label}</label>
      )}

      {/* Search */}
      <Input
        type="text"
        placeholder="Search icons..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="h-11 bg-white border-2 border-gray-200 focus:border-blue-500 rounded-lg transition-all"
      />

      {/* Icon Grid */}
      <div className="grid grid-cols-6 gap-2.5 max-h-52 overflow-y-auto p-3 bg-white border-2 border-gray-200 rounded-xl">
        {filteredIcons.map(({ name, Icon }) => {
          const isSelected = value === name
          return (
            <button
              key={name}
              type="button"
              onClick={() => onChange(name)}
              className={cn(
                'flex items-center justify-center h-14 w-14 rounded-xl transition-all duration-200 hover:scale-105',
                isSelected
                  ? 'bg-blue-500 text-white shadow-lg scale-105'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 shadow-sm hover:shadow-md'
              )}
              title={name}
            >
              <Icon className="h-6 w-6" />
            </button>
          )
        })}
      </div>

      {filteredIcons.length === 0 && (
        <div className="text-center text-sm text-gray-500 py-6 bg-gray-50 rounded-lg border-2 border-gray-200 border-dashed">
          No icons found
        </div>
      )}
    </div>
  )
}

// Helper function to get Icon component by name
export const getIconByName = (iconName: string | null) => {
  if (!iconName) return FolderKanban
  const icon = AVAILABLE_ICONS.find((i) => i.name === iconName)
  return icon?.Icon || FolderKanban
}
