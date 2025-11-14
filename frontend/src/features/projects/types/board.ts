/**
 * Board Types
 * Type definitions for Kanban Board View
 */

import type { StoryStatus, StoryType, StoryPriority } from './project'

// ==================== Story ====================

/**
 * Story Interface (simplified for board view)
 */
export interface Story {
  id: number
  title: string
  description: string | null
  story_type: StoryType
  priority: StoryPriority
  status: StoryStatus
  story_points: number | null
  acceptance_criteria: string | null
  epic_id: number | null
  project_id: number
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
  blocked_at: string | null
  blocked_reason: string | null
}

/**
 * Story with assigned agents
 */
export interface StoryWithAgents extends Story {
  assigned_agents: Agent[]
}

/**
 * Agent Interface
 */
export interface Agent {
  id: number
  name: string
  agent_type: string
  project_id: number
}

// ==================== Board View ====================

/**
 * Board Column with stories
 */
export interface BoardColumn {
  status: StoryStatus
  name: string
  wip_limit: number | null
  current_wip: number
  stories: Story[]
}

/**
 * Complete Board View
 */
export interface BoardView {
  project_id: number
  columns: BoardColumn[]
  total_stories: number
  blocked_count: number
}

/**
 * Story Movement Request
 */
export interface MoveStoryRequest {
  story_id: number
  from_status: StoryStatus
  to_status: StoryStatus
}

/**
 * WIP Limit Status
 */
export interface WIPLimitStatus {
  column: StoryStatus
  current: number
  limit: number | null
  is_exceeded: boolean
  is_warning: boolean // 80% of limit
}
