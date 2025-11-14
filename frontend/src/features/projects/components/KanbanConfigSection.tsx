import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Info, AlertTriangle } from 'lucide-react'
import type { KanbanPolicy, StoryStatus } from '@/features/projects/types'
import { DEFAULT_KANBAN_POLICY, hasWIPLimit } from '@/features/projects/types'
import { cn } from '@/lib/utils'

interface KanbanConfigSectionProps {
  kanbanPolicy: KanbanPolicy
  onChange: (policy: KanbanPolicy) => void
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
  const doneColumns = policy.columns.filter((c) => ['DONE', 'BLOCKED', 'ARCHIVED'].includes(c.status))

  return (
    <div className="space-y-6">
      {/* Info Alert */}
      <Alert className="glass-card border-blue-500/30 bg-blue-500/5">
        <Info className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-sm text-slate-700">
          Configure WIP (Work In Progress) limits for columns. Recommended: IN_PROGRESS=3, REVIEW=2,
          TESTING=2. Leave empty for unlimited.
        </AlertDescription>
      </Alert>

      {/* Kanban Workflow Visualization */}
      <div className="space-y-6">
        {/* Backlog Stage */}
        {todoColumn && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-600 uppercase tracking-wider">Backlog</h4>
            <div className="glass-premium p-4 rounded-xl">
              <ColumnConfig column={todoColumn} onChange={handleWIPLimitChange} disabled />
            </div>
          </div>
        )}

        {/* In Progress Stages */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-slate-600 uppercase tracking-wider">
              In Progress (WIP Limited)
            </h4>
            <AlertTriangle className="h-4 w-4 text-amber-600" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {inProgressColumns.map((column) => (
              <div key={column.status} className="glass-premium p-4 rounded-xl">
                <ColumnConfig column={column} onChange={handleWIPLimitChange} />
              </div>
            ))}
          </div>
        </div>

        {/* Done Stages */}
        <div className="space-y-3">
          <h4 className="text-sm font-bold text-slate-600 uppercase tracking-wider">
            Completed & Blocked
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {doneColumns.map((column) => (
              <div key={column.status} className="glass-card p-4 rounded-xl opacity-75">
                <ColumnConfig column={column} onChange={handleWIPLimitChange} disabled />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Column Configuration Component
interface ColumnConfigProps {
  column: { status: StoryStatus; name: string; wip_limit: number | null; description: string }
  onChange: (status: StoryStatus, value: string) => void
  disabled?: boolean
}

const ColumnConfig = ({ column, onChange, disabled = false }: ColumnConfigProps) => {
  const canHaveWIPLimit = hasWIPLimit(column.status)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <Label className="text-sm font-bold text-foreground">{column.name}</Label>
          <p className="text-xs text-muted-foreground mt-1">{column.description}</p>
        </div>
        <div
          className={cn(
            'px-2 py-1 rounded-lg text-xs font-mono font-bold',
            canHaveWIPLimit
              ? 'bg-gradient-to-r from-blue-500/20 to-purple-600/20 text-blue-700'
              : 'bg-slate-200 text-slate-600'
          )}
        >
          {column.status}
        </div>
      </div>

      {canHaveWIPLimit && !disabled && (
        <div className="space-y-2">
          <Label htmlFor={`wip-${column.status}`} className="text-xs text-slate-600">
            WIP Limit
          </Label>
          <Input
            id={`wip-${column.status}`}
            type="number"
            min="1"
            max="20"
            value={column.wip_limit || ''}
            onChange={(e) => onChange(column.status, e.target.value)}
            placeholder="Unlimited"
            className="bg-white/60 border-white/40 h-10"
          />
          <p className="text-xs text-muted-foreground">
            {column.wip_limit
              ? `Limited to ${column.wip_limit} stories`
              : 'No limit set (not recommended)'}
          </p>
        </div>
      )}

      {(!canHaveWIPLimit || disabled) && (
        <div className="pt-2">
          <p className="text-xs text-slate-500 italic">No WIP limit for this column</p>
        </div>
      )}
    </div>
  )
}
