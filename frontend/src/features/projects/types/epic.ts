export interface Epic {
  id: number;
  title: string;
  description: string | null;
  project_id: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface CreateEpicData {
  title: string;
  description?: string;
  project_id: number;
}

export interface UpdateEpicData {
  title?: string;
  description?: string;
}

export interface EpicProgress {
  epic_id: number;
  epic_title: string;
  total_stories: number;
  completed_stories: number;
  in_progress_stories: number;
  blocked_stories: number;
  completion_percentage: number;
  by_status: Record<string, number>;
}
