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
    <div className="space-y-3">
      {label && <label className="text-sm font-semibold text-foreground">{label}</label>}

      {/* Search */}
      <Input
        type="text"
        placeholder="Search icons..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="bg-white/50 backdrop-blur-xl border-white/30"
      />

      {/* Icon Grid */}
      <div className="grid grid-cols-6 gap-2 max-h-64 overflow-y-auto p-2 glass rounded-xl">
        {filteredIcons.map(({ name, Icon }) => {
          const isSelected = value === name
          return (
            <button
              key={name}
              type="button"
              onClick={() => onChange(name)}
              className={cn(
                'flex items-center justify-center h-12 w-12 rounded-lg transition-all duration-300 hover:scale-110 hover:bg-white/40',
                isSelected
                  ? 'bg-gradient-to-br from-blue-500/20 to-purple-600/20 ring-2 ring-blue-500 scale-110'
                  : 'bg-white/20 hover:bg-white/30'
              )}
              title={name}
            >
              <Icon
                className={cn(
                  'h-5 w-5 transition-colors',
                  isSelected ? 'text-blue-600' : 'text-slate-600'
                )}
              />
            </button>
          )
        })}
      </div>

      {filteredIcons.length === 0 && (
        <div className="text-center text-sm text-muted-foreground py-4">No icons found</div>
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
