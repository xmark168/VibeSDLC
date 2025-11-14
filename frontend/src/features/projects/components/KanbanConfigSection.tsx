import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { CheckCircle2, Circle, Archive, XCircle, Loader2, Clock, FileCheck, CheckSquare } from 'lucide-react'
import type { KanbanPolicy, StoryStatus } from '@/features/projects/types'
import { DEFAULT_KANBAN_POLICY, hasWIPLimit } from '@/features/projects/types'
import { cn } from '@/lib/utils'

interface KanbanConfigSectionProps {
  kanbanPolicy: KanbanPolicy
  onChange: (policy: KanbanPolicy) => void
}

// Status icon mapping
const getStatusIcon = (status: StoryStatus) => {
  const icons = {
    TODO: Circle,
    IN_PROGRESS: Loader2,
    REVIEW: FileCheck,
    TESTING: CheckSquare,
    DONE: CheckCircle2,
    BLOCKED: XCircle,
    ARCHIVED: Archive,
  }
  return icons[status] || Circle
}

// Status color mapping
const getStatusColor = (status: StoryStatus) => {
  const colors = {
    TODO: 'text-gray-500 bg-gray-50 border-gray-200',
    IN_PROGRESS: 'text-blue-600 bg-blue-50 border-blue-200',
    REVIEW: 'text-purple-600 bg-purple-50 border-purple-200',
    TESTING: 'text-amber-600 bg-amber-50 border-amber-200',
    DONE: 'text-green-600 bg-green-50 border-green-200',
    BLOCKED: 'text-red-600 bg-red-50 border-red-200',
    ARCHIVED: 'text-slate-500 bg-slate-50 border-slate-200',
  }
  return colors[status] || 'text-gray-500 bg-gray-50 border-gray-200'
}

// Accent border color for cards
const getAccentBorder = (status: StoryStatus) => {
  const borders = {
    TODO: 'border-l-gray-400',
    IN_PROGRESS: 'border-l-blue-500',
    REVIEW: 'border-l-purple-500',
    TESTING: 'border-l-amber-500',
    DONE: 'border-l-green-500',
    BLOCKED: 'border-l-red-500',
    ARCHIVED: 'border-l-slate-400',
  }
  return borders[status] || 'border-l-gray-400'
}

export const KanbanConfigSection = ({ kanbanPolicy, onChange }: KanbanConfigSectionProps) => {
  const [policy, setPolicy] = useState<KanbanPolicy>(kanbanPolicy || DEFAULT_KANBAN_POLICY)

  useEffect(() => {
    setPolicy(kanbanPolicy || DEFAULT_KANBAN_POLICY)
  }, [kanbanPolicy])

  const handleWIPLimitChange = (status: StoryStatus, value: string) => {
    const newLimit = value === '' ? null : parseInt(value, 10)

    const updatedColumns = policy.columns.map((col) =>
      col.status === status ? { ...col, wip_limit: newLimit } : col
    )

    const updatedPolicy = {
      ...policy,
      columns: updatedColumns,
    }

    setPolicy(updatedPolicy)
    onChange(updatedPolicy)
  }

  // Group columns into workflow stages
  const todoColumn = policy.columns.find((c) => c.status === 'TODO')
  const inProgressColumns = policy.columns.filter((c) =>
    ['IN_PROGRESS', 'REVIEW', 'TESTING'].includes(c.status)
  )
  const terminalColumns = policy.columns.filter((c) => ['DONE', 'BLOCKED', 'ARCHIVED'].includes(c.status))

  return (
    <div className="space-y-8">
      {/* Kanban Workflow - Single Column Layout */}
      <div className="space-y-8">
        {/* Section 1: Backlog */}
        {todoColumn && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-1 bg-gray-400 rounded-full"></div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Backlog</h3>
                <p className="text-sm text-gray-600">Starting point for all stories</p>
              </div>
            </div>
            <ColumnCard column={todoColumn} onChange={handleWIPLimitChange} disabled />
          </div>
        )}

        {/* Section 2: Active Work - Editable */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-1 bg-gradient-to-b from-blue-500 via-purple-500 to-amber-500 rounded-full"></div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Active Work</h3>
              <p className="text-sm text-gray-600">Columns with WIP limits to optimize flow</p>
            </div>
          </div>
          <div className="space-y-3">
            {inProgressColumns.map((column) => (
              <ColumnCard key={column.status} column={column} onChange={handleWIPLimitChange} />
            ))}
          </div>
        </div>

        {/* Section 3: Terminal States */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-1 bg-gray-400 rounded-full"></div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Terminal States</h3>
              <p className="text-sm text-gray-600">Final destinations for stories</p>
            </div>
          </div>
          <div className="space-y-3">
            {terminalColumns.map((column) => (
              <ColumnCard key={column.status} column={column} onChange={handleWIPLimitChange} disabled />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Column Card Component - Modern Card Style
interface ColumnCardProps {
  column: { status: StoryStatus; name: string; wip_limit: number | null; description: string }
  onChange: (status: StoryStatus, value: string) => void
  disabled?: boolean
}

const ColumnCard = ({ column, onChange, disabled = false }: ColumnCardProps) => {
  const canHaveWIPLimit = hasWIPLimit(column.status)
  const StatusIcon = getStatusIcon(column.status)
  const isEditable = canHaveWIPLimit && !disabled

  return (
    <div
      className={cn(
        'bg-white border-2 rounded-xl p-5 transition-all duration-200',
        'border-l-4',
        getAccentBorder(column.status),
        isEditable
          ? 'shadow-md hover:shadow-lg border-gray-200 hover:border-gray-300'
          : 'shadow-sm border-gray-100 bg-gray-50/30'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: Column Info */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg border-2', getStatusColor(column.status))}>
              <StatusIcon className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-base font-bold text-gray-900">{column.name}</h4>
              <p className="text-sm text-gray-600 mt-0.5">{column.description}</p>
            </div>
          </div>

          {/* Status Badge */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {column.status}
            </span>
            {isEditable && (
              <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-1 rounded">
                ✏️ Editable
              </span>
            )}
          </div>
        </div>

        {/* Right: WIP Limit Control */}
        {isEditable ? (
          <div className="w-48 space-y-2">
            <Label htmlFor={`wip-${column.status}`} className="text-sm font-semibold text-gray-700">
              WIP Limit
            </Label>
            <Input
              id={`wip-${column.status}`}
              type="number"
              min="1"
              max="20"
              value={column.wip_limit || ''}
              onChange={(e) => onChange(column.status, e.target.value)}
              placeholder="∞ Unlimited"
              className="h-12 text-lg font-semibold text-center border-2 border-gray-300 focus:border-blue-500 transition-all"
            />
            <div className="text-xs text-center">
              {column.wip_limit ? (
                <span className="text-green-700 font-medium flex items-center justify-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Max {column.wip_limit} {column.wip_limit === 1 ? 'story' : 'stories'}
                </span>
              ) : (
                <span className="text-amber-600 font-medium flex items-center justify-center gap-1">
                  <Clock className="h-3 w-3" />
                  No limit (not recommended)
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="w-48 flex items-center justify-center">
            <div className="text-center space-y-1 py-4">
              <div className="text-2xl font-bold text-gray-400">∞</div>
              <p className="text-xs text-gray-500 font-medium">No WIP limit</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
