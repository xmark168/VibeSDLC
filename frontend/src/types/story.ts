// Story-related types

export type StoryStatus = 'Todo' | 'InProgress' | 'Review' | 'Done' | 'Archived';
export type StoryType = 'UserStory' | 'EnablerStory';

export interface Story {
  id: string;
  project_id: string;
  parent_id?: string | null;
  type: StoryType;
  title: string;
  description?: string;
  status: StoryStatus;
  epic_id?: string | null;
  assignee_id?: string | null;
  reviewer_id?: string | null;
  acceptance_criteria?: string[];
  requirements?: string[];
  rank?: number | null;
  story_point?: number | null;
  priority?: number | null;
  dependencies: string[];
  completed_at?: string | null;
  started_at?: string | null;
  review_started_at?: string | null;
  created_at: string;
  updated_at: string;
  parent?: Story | null;
  children?: Story[];
  comments?: Comment[]; // if available
}

export interface CreateStoryResponse {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: StoryStatus;
  created_at: string;
  updated_at: string;
}

export interface UpdateStoryParams {
  title?: string;
  description?: string;
  status?: StoryStatus;
  story_type?: StoryType;
  priority?: number;
  estimated_hours?: number;
  actual_hours?: number;
  assigned_to?: string;
  sprint_id?: string;
  epic_id?: string;
  parent_story_id?: string;
  tags?: string[];
  acceptance_criteria?: string[];
  requirements?: string[];
  business_value?: number;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';
  target_release?: string;
  dependencies?: string[];
  blocked_by?: string;
  blocking?: string[];
  attachments?: string[];
  labels?: string[];
}

export interface StoryFormData {
  title: string;
  description: string;
  type: StoryType;
  story_point?: number;
  priority?: "High" | "Medium" | "Low";
  acceptance_criteria: string[];
  requirements: string[];
  dependencies: string[];  // List of story IDs that must be completed first
}