import { apiClient } from "./client"

export interface Artifact {
  id: string
  project_id: string
  agent_id?: string
  agent_name: string
  artifact_type: string
  title: string
  description?: string
  content: any
  file_path?: string
  version: number
  parent_artifact_id?: string
  status: string
  reviewed_by_user_id?: string
  reviewed_at?: string
  review_feedback?: string
  tags: string[]
  extra_metadata?: any
  created_at: string
  updated_at: string
}

export const artifactsApi = {
  // Get artifact by ID
  getArtifact: async (artifactId: string): Promise<Artifact> => {
    const response = await apiClient.get(`/artifacts/${artifactId}`)
    return response.data
  },

  // List artifacts for a project
  listProjectArtifacts: async (
    projectId: string,
    params?: {
      artifact_type?: string
      status?: string
      limit?: number
    },
  ): Promise<Artifact[]> => {
    const response = await apiClient.get(
      `/artifacts/projects/${projectId}/artifacts`,
      {
        params,
      },
    )
    return response.data.artifacts || []
  },

  // Update artifact status
  updateArtifactStatus: async (
    artifactId: string,
    status: string,
    feedback?: string,
  ): Promise<Artifact> => {
    const response = await apiClient.patch(`/artifacts/${artifactId}/status`, {
      status,
      feedback,
    })
    return response.data
  },

  // Create new version
  createVersion: async (
    artifactId: string,
    newContent: any,
    description?: string,
  ): Promise<Artifact> => {
    const response = await apiClient.post(`/artifacts/${artifactId}/version`, {
      new_content: newContent,
      description,
    })
    return response.data
  },

  // Get latest version
  getLatestVersion: async (
    projectId: string,
    artifactType: string,
    title?: string,
  ): Promise<Artifact | null> => {
    const response = await apiClient.get(
      `/artifacts/projects/${projectId}/artifacts/latest`,
      {
        params: {
          artifact_type: artifactType,
          title,
        },
      },
    )
    return response.data
  },
}
