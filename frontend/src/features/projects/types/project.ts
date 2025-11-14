/**
 * Project Types
 * Type definitions for Projects and Kanban configuration
 */

// ==================== Enums ====================

/**
 * Story Status Enum - matches backend StoryStatus
 * These are the fixed column types in our Lean Kanban system
 */
export enum StoryStatus {
  TODO = 'TODO',
  IN_PROGRESS = 'IN_PROGRESS',
  REVIEW = 'REVIEW',
  TESTING = 'TESTING',
  DONE = 'DONE',
  BLOCKED = 'BLOCKED',
  ARCHIVED = 'ARCHIVED',
}

/**
 * Story Type Enum
 */
export enum StoryType {
  USER_STORY = 'USER_STORY',
  ENABLER_STORY = 'ENABLER_STORY',
}

/**
 * Story Priority Enum
 */
export enum StoryPriority {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

// ==================== Kanban Configuration ====================

/**
 * Kanban Column Configuration
 */
export interface KanbanColumn {
  status: StoryStatus
  name: string
  wip_limit: number | null
  position: number
  description: string
}

/**
 * Workflow Rules Configuration
 */
export interface WorkflowRules {
  allowed_transitions: Record<StoryStatus, StoryStatus[]>
  completion_requirements: {
    acceptance_criteria_required: boolean
    min_agents_assigned: number
  }
}

/**
 * Complete Kanban Policy Configuration
 */
export interface KanbanPolicy {
  version: string
  columns: KanbanColumn[]
  workflow_rules: WorkflowRules
}

// ==================== Project ====================

/**
 * Tech Stack (nested object)
 */
export interface TechStack {
  id: number
  name: string
  description: string | null
}

/**
 * Complete Project Interface
 */
export interface Project {
  id: number
  code: string
  name: string
  description: string | null
  color: string | null // Hex color code, e.g., "#FF5733"
  icon: string | null // Icon name or emoji
  working_directory: string | null
  owner_id: number
  tech_stack_id: number | null
  kanban_policy: KanbanPolicy | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  tech_stack?: TechStack | null

  // Computed fields (may come from backend joins)
  active_stories_count?: number
  progress?: number
}

/**
 * Project Create Data
 */
export interface CreateProjectData {
  code: string
  name: string
  description?: string
  color?: string // Hex color code
  icon?: string // Icon name or emoji
  working_directory?: string
  tech_stack_id?: number
  kanban_policy?: KanbanPolicy
}

/**
 * Project Update Data
 */
export interface UpdateProjectData {
  code?: string
  name?: string
  description?: string
  color?: string
  icon?: string
  working_directory?: string
  tech_stack_id?: number
  kanban_policy?: KanbanPolicy
}

/**
 * Project Filter Options
 */
export interface ProjectFilters {
  search?: string // Search by name or code
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'progress'
  sort_order?: 'asc' | 'desc'
}

/**
 * Project View Mode
 */
export type ProjectViewMode = 'grid' | 'table'

// ==================== Default Values ====================

/**
 * Default Kanban Policy (matches backend default)
 */
export const DEFAULT_KANBAN_POLICY: KanbanPolicy = {
  version: '1.0',
  columns: [
    {
      status: StoryStatus.TODO,
      name: 'Backlog',
      wip_limit: null,
      position: 0,
      description: 'Stories ready to be started',
    },
    {
      status: StoryStatus.IN_PROGRESS,
      name: 'In Progress',
      wip_limit: 3,
      position: 1,
      description: 'Stories currently being worked on',
    },
    {
      status: StoryStatus.REVIEW,
      name: 'Code Review',
      wip_limit: 2,
      position: 2,
      description: 'Stories under review',
    },
    {
      status: StoryStatus.TESTING,
      name: 'Testing',
      wip_limit: 2,
      position: 3,
      description: 'Stories being tested',
    },
    {
      status: StoryStatus.DONE,
      name: 'Completed',
      wip_limit: null,
      position: 4,
      description: 'Completed stories',
    },
    {
      status: StoryStatus.BLOCKED,
      name: 'Blocked',
      wip_limit: null,
      position: 5,
      description: 'Stories that are blocked',
    },
    {
      status: StoryStatus.ARCHIVED,
      name: 'Archived',
      wip_limit: null,
      position: 6,
      description: 'Archived stories',
    },
  ],
  workflow_rules: {
    allowed_transitions: {
      [StoryStatus.TODO]: [StoryStatus.IN_PROGRESS],
      [StoryStatus.IN_PROGRESS]: [StoryStatus.REVIEW, StoryStatus.BLOCKED],
      [StoryStatus.REVIEW]: [StoryStatus.IN_PROGRESS, StoryStatus.TESTING, StoryStatus.BLOCKED],
      [StoryStatus.TESTING]: [StoryStatus.REVIEW, StoryStatus.DONE, StoryStatus.BLOCKED],
      [StoryStatus.BLOCKED]: [
        StoryStatus.TODO,
        StoryStatus.IN_PROGRESS,
        StoryStatus.REVIEW,
        StoryStatus.TESTING,
      ],
      [StoryStatus.DONE]: [StoryStatus.ARCHIVED],
      [StoryStatus.ARCHIVED]: [],
    },
    completion_requirements: {
      acceptance_criteria_required: true,
      min_agents_assigned: 1,
    },
  },
}

/**
 * Preset Project Colors
 */
export const PROJECT_COLORS = [
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#06B6D4', // Cyan
  '#6366F1', // Indigo
  '#14B8A6', // Teal
  '#F97316', // Orange
  '#84CC16', // Lime
  '#A855F7', // Violet
]

/**
 * Helper function to get column display name
 */
export const getColumnName = (status: StoryStatus): string => {
  const column = DEFAULT_KANBAN_POLICY.columns.find((col) => col.status === status)
  return column?.name || status
}

/**
 * Helper function to check if column has WIP limit
 */
export const hasWIPLimit = (status: StoryStatus): boolean => {
  return [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW, StoryStatus.TESTING].includes(status)
}
