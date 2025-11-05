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

  product_backlog: {
    metadata: {
      product_name: 'TaskMaster Pro',
      version: 'v1.0',
      total_items: 12,
      total_epics: 2,
      total_user_stories: 4,
      total_tasks: 2,
      total_subtasks: 4,
      total_story_points: 34,
      total_estimate_hours: 56,
    },
    items: [
      {
        id: 'EPIC-001',
        type: 'Epic',
        parent_id: null,
        title: 'Core Task Management',
        description: 'Complete task management system including creation, editing, and deletion',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: null,
        acceptance_criteria: [],
        dependencies: [],
        labels: ['core', 'task-management'],
        task_type: null,
        business_value: 'Enable users to manage their daily tasks efficiently',
      },
      {
        id: 'US-001',
        type: 'User Story',
        parent_id: 'EPIC-001',
        title: 'As a user, I want to create tasks with title and description so that I can track my work',
        description: 'Basic task creation functionality with title, description, and due date',
        rank: null,
        status: 'Backlog',
        story_point: 5,
        estimate_value: null,
        acceptance_criteria: [
          'Given user is on dashboard, When user clicks create task, Then task form appears',
          'Given task form is open, When user enters title and description, Then task is saved',
          'Given task is saved, When user views task list, Then new task appears',
        ],
        dependencies: [],
        labels: ['task-management', 'core'],
        task_type: null,
        business_value: 'Core feature for task tracking',
      },
      {
        id: 'SUB-001',
        type: 'Sub-task',
        parent_id: 'US-001',
        title: 'Implement task creation API endpoint',
        description: 'Create POST /api/tasks endpoint with validation',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: 8,
        acceptance_criteria: [
          'API endpoint accepts POST /api/tasks',
          'Validates required fields (title, description)',
          'Returns 201 status with created task',
        ],
        dependencies: [],
        labels: ['backend', 'api'],
        task_type: 'Development',
        business_value: null,
      },
      {
        id: 'SUB-002',
        type: 'Sub-task',
        parent_id: 'US-001',
        title: 'Create task form UI component',
        description: 'Build React form component for task creation',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: 6,
        acceptance_criteria: [
          'Form has title and description fields',
          'Submit button calls API endpoint',
          'Success message shown after creation',
        ],
        dependencies: ['SUB-001'],
        labels: ['frontend', 'ui'],
        task_type: 'Development',
        business_value: null,
      },
      {
        id: 'US-002',
        type: 'User Story',
        parent_id: 'EPIC-001',
        title: 'As a user, I want to view all my tasks so that I can see what needs to be done',
        description: 'Task list view with filtering and sorting',
        rank: null,
        status: 'Backlog',
        story_point: 8,
        estimate_value: null,
        acceptance_criteria: [
          'Given user is logged in, When user opens task list, Then all tasks are displayed',
          'Given tasks are displayed, When user filters by status, Then only matching tasks show',
        ],
        dependencies: ['US-001'],
        labels: ['task-management', 'core'],
        task_type: null,
        business_value: 'Allow users to organize and prioritize work',
      },
      {
        id: 'EPIC-002',
        type: 'Epic',
        parent_id: null,
        title: 'Real-time Collaboration',
        description: 'WebSocket-based real-time updates for team collaboration',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: null,
        acceptance_criteria: [],
        dependencies: ['EPIC-001'],
        labels: ['collaboration', 'real-time'],
        task_type: null,
        business_value: 'Enable seamless team collaboration',
      },
      {
        id: 'US-003',
        type: 'User Story',
        parent_id: 'EPIC-002',
        title: 'As a team member, I want to see live updates when others modify tasks so that I stay in sync',
        description: 'Real-time task updates via WebSocket',
        rank: null,
        status: 'Backlog',
        story_point: 13,
        estimate_value: null,
        acceptance_criteria: [
          'Given user is viewing task list, When another user creates a task, Then new task appears automatically',
          'Given user is viewing a task, When another user edits it, Then changes update in real-time',
        ],
        dependencies: ['US-001', 'US-002'],
        labels: ['collaboration', 'real-time', 'websocket'],
        task_type: null,
        business_value: 'Reduce conflicts and improve team awareness',
      },
      {
        id: 'SUB-003',
        type: 'Sub-task',
        parent_id: 'US-003',
        title: 'Setup WebSocket server infrastructure',
        description: 'Configure WebSocket server with authentication',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: 16,
        acceptance_criteria: [
          'WebSocket server accepts connections',
          'JWT authentication implemented',
          'Connection pooling by project',
        ],
        dependencies: [],
        labels: ['backend', 'infrastructure', 'websocket'],
        task_type: 'Development',
        business_value: null,
      },
      {
        id: 'SUB-004',
        type: 'Sub-task',
        parent_id: 'US-003',
        title: 'Implement real-time task update broadcasting',
        description: 'Broadcast task changes to all connected users',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: 12,
        acceptance_criteria: [
          'Task create/update/delete events broadcast to project members',
          'Events include full task data',
          'Optimistic UI updates on sender side',
        ],
        dependencies: ['SUB-003'],
        labels: ['backend', 'websocket'],
        task_type: 'Development',
        business_value: null,
      },
      {
        id: 'US-004',
        type: 'User Story',
        parent_id: 'EPIC-001',
        title: 'As a user, I want to assign tasks to team members so that work is distributed',
        description: 'Task assignment functionality',
        rank: null,
        status: 'Backlog',
        story_point: 8,
        estimate_value: null,
        acceptance_criteria: [
          'Given user is editing a task, When user selects assignee, Then task is assigned',
          'Given task is assigned, When user views task, Then assignee name is displayed',
        ],
        dependencies: ['US-001'],
        labels: ['task-management', 'collaboration'],
        task_type: null,
        business_value: 'Enable task delegation and accountability',
      },
      {
        id: 'TASK-001',
        type: 'Task',
        parent_id: 'EPIC-001',
        title: 'Setup database schema for tasks',
        description: 'Design and implement PostgreSQL schema for task storage',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: null,
        acceptance_criteria: [
          'Task table created with all required fields',
          'Foreign keys and indexes configured',
          'Migration scripts created',
        ],
        dependencies: [],
        labels: ['database', 'infrastructure'],
        task_type: 'Infrastructure',
        business_value: null,
      },
      {
        id: 'TASK-002',
        type: 'Task',
        parent_id: 'EPIC-002',
        title: 'Research WebSocket scalability solutions',
        description: 'Evaluate Redis pub/sub vs direct WebSocket connections',
        rank: null,
        status: 'Backlog',
        story_point: null,
        estimate_value: null,
        acceptance_criteria: [
          'Document comparison of Redis pub/sub vs direct connections',
          'Recommend solution based on team size constraints',
          'Estimate implementation effort',
        ],
        dependencies: [],
        labels: ['research', 'websocket', 'scalability'],
        task_type: 'Research',
        business_value: null,
      },
    ],
  },
}
