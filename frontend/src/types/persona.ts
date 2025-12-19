export interface PersonaTemplate {
  id: string
  name: string
  role_type: string
  avatar?: string | null
  personality_traits: string[]
  communication_style: string
  persona_metadata: Record<string, any>
  is_active: boolean
  display_order: number
  created_at: string
  updated_at: string
}

export interface PersonaCreate {
  name: string
  role_type: string
  avatar?: string | null
  personality_traits: string[]
  communication_style: string
  persona_metadata?: Record<string, any>
  display_order?: number
}

export interface PersonaUpdate {
  name?: string
  role_type?: string
  avatar?: string | null
  personality_traits?: string[]
  communication_style?: string
  persona_metadata?: Record<string, any>
  display_order?: number
  is_active?: boolean
}

export interface PersonaWithUsageStats extends PersonaTemplate {
  active_agents_count: number
  total_agents_created: number
}

export type RoleType =
  | "team_leader"
  | "business_analyst"
  | "developer"
  | "tester"

export const roleTypeLabels: Record<RoleType, string> = {
  team_leader: "Team Leader",
  business_analyst: "Business Analyst",
  developer: "Developer",
  tester: "Tester",
}

export const roleTypeColors: Record<RoleType, string> = {
  team_leader: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  business_analyst: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  developer: "bg-green-500/10 text-green-400 border-green-500/20",
  tester: "bg-amber-500/10 text-amber-400 border-amber-500/20",
}
