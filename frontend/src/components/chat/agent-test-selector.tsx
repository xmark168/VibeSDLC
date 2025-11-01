import { useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Beaker, Info } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export type AgentTestMode = 'full' | 'gatherer' | 'vision' | 'backlog' | 'priority'

interface AgentTestSelectorProps {
  value: AgentTestMode
  onChange: (mode: AgentTestMode) => void
}

const AGENT_MODES = [
  {
    value: 'full' as AgentTestMode,
    label: '🔄 Full Workflow',
    description: 'Run complete PO Agent workflow (Gatherer → Vision → Backlog → Priority)',
  },
  {
    value: 'gatherer' as AgentTestMode,
    label: '📋 Gatherer Only',
    description: 'Test Gatherer Agent: collect product information and create brief',
  },
  {
    value: 'vision' as AgentTestMode,
    label: '🌟 Vision Only',
    description: 'Test Vision Agent: generate product vision & PRD (uses mock brief)',
  },
  {
    value: 'backlog' as AgentTestMode,
    label: '📝 Backlog Only',
    description: 'Test Backlog Agent: create user stories and backlog (uses mock vision)',
  },
  {
    value: 'priority' as AgentTestMode,
    label: '🎯 Priority Only',
    description: 'Test Priority Agent: prioritize items and create sprint plan (uses mock backlog)',
  },
]

export function AgentTestSelector({ value, onChange }: AgentTestSelectorProps) {
  const [showInfo, setShowInfo] = useState(false)

  const currentMode = AGENT_MODES.find((m) => m.value === value)

  return (
    <div className="flex items-center gap-2 p-2 bg-muted/30 rounded-lg border border-border/50">
      <Beaker className="w-4 h-4 text-muted-foreground flex-shrink-0" />
      <span className="text-xs text-muted-foreground flex-shrink-0">Test Mode:</span>

      <Select value={value} onValueChange={(v) => onChange(v as AgentTestMode)}>
        <SelectTrigger className="h-8 text-xs w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {AGENT_MODES.map((mode) => (
            <SelectItem key={mode.value} value={mode.value} className="text-xs">
              {mode.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <TooltipProvider>
        <Tooltip open={showInfo} onOpenChange={setShowInfo}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 flex-shrink-0"
              onMouseEnter={() => setShowInfo(true)}
              onMouseLeave={() => setShowInfo(false)}
            >
              <Info className="w-3 h-3 text-muted-foreground" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <p className="text-xs">{currentMode?.description}</p>
            {value !== 'full' && value !== 'gatherer' && (
              <p className="text-xs text-yellow-500 mt-1">
                ⚠️ Uses mock data - just type anything to test!
              </p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}

// Mock data generators for testing
export const MOCK_DATA = {
  product_brief: {
    product_name: 'TaskMaster Pro',
    description:
      'A modern task management application for small teams with real-time collaboration features',
    target_audience: ['Small teams (5-20 people)', 'Freelancers', 'Startup teams'],
    key_features: [
      'Real-time task updates',
      'Kanban board view',
      'Team collaboration',
      'File attachments',
      'Comments and mentions',
    ],
    benefits: [
      'Improved team productivity',
      'Better task visibility',
      'Reduced email clutter',
    ],
    competitors: ['Trello', 'Asana', 'Monday.com'],
    completeness_note: 'Complete product brief for testing',
  },

  product_vision: {
    draft_vision_statement:
      'Empower small teams to collaborate seamlessly and achieve their goals through intuitive task management',
    experience_principles: [
      'Simplicity first - no overwhelming features',
      'Real-time updates - stay in sync',
      'Accessible anywhere - web and mobile',
    ],
    problem_summary:
      'Small teams struggle with fragmented communication and task tracking across multiple tools',
    audience_segments: [
      {
        name: 'Startup Teams',
        description: 'Fast-moving teams that need quick setup',
        needs: ['Quick onboarding', 'Flexible workflows'],
        pain_points: ['Complex tools', 'High costs'],
      },
    ],
    functional_requirements: [
      {
        name: 'Task Management',
        description: 'Create, assign, and track tasks',
        priority: 'High',
        user_stories: ['As a user, I can create tasks with descriptions and due dates'],
        acceptance_criteria: ['Task form validates required fields', 'Due dates support calendar picker'],
      },
    ],
    performance_requirements: ['Page load under 2 seconds', 'Support 100 concurrent users'],
    security_requirements: ['End-to-end encryption', 'Role-based access control'],
    ux_requirements: ['Mobile responsive', 'Dark mode support'],
    scope_capabilities: ['Task CRUD', 'Real-time sync', 'User auth'],
    scope_non_goals: ['Time tracking', 'Invoicing', 'CRM features'],
    dependencies: ['PostgreSQL', 'WebSocket server', 'Cloud storage for files'],
    risks: ['WebSocket scalability', 'Real-time sync conflicts'],
    assumptions: ['Users have stable internet', 'Teams under 20 people'],
  },
}
