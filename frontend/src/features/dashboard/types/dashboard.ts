// Dashboard Metrics Types

export interface MetricCard {
  id: string
  title: string
  value: number | string
  change?: number // Percentage change
  trend?: 'up' | 'down' | 'neutral'
  icon: string
  description?: string
}

export interface DashboardMetrics {
  totalProjects: number
  activeStories: number
  throughput: number
  avgCycleTime: number
  wip: number
  blockedStories: number
}

// Project Types
export interface Project {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
  user_id: number
  tech_stack_id: number | null
  kanban_policy_id: number | null
  active_stories_count?: number
  progress?: number
}

// Story Types
export interface Story {
  id: number
  title: string
  description: string | null
  story_points: number | null
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: 'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'REVIEW' | 'DONE'
  epic_id: number | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

// Activity Feed Types
export interface Activity {
  id: string
  type: 'story_created' | 'story_updated' | 'story_completed' | 'agent_assigned' | 'status_changed'
  title: string
  description: string
  timestamp: string
  user?: string
  story?: {
    id: number
    title: string
  }
  project?: {
    id: number
    name: string
  }
}

// Chart Data Types
export interface CumulativeFlowData {
  date: string
  backlog: number
  todo: number
  in_progress: number
  review: number
  done: number
}

export interface ThroughputData {
  date: string
  completed: number
}

export interface CycleTimeData {
  date: string
  avgCycleTime: number
}

// Dashboard Response Type
export interface DashboardData {
  metrics: DashboardMetrics
  projects: Project[]
  recentActivities: Activity[]
  cumulativeFlow: CumulativeFlowData[]
  throughput: ThroughputData[]
  cycleTime: CycleTimeData[]
}
