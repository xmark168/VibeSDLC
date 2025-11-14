import axiosInstance from '@/core/lib/axios'
import type { CumulativeFlowData } from '@/features/dashboard/types/dashboard'

// Base parameters - project_id is REQUIRED for all metrics endpoints
export interface BaseMetricsParams {
  project_id: number
}

// Parameters for endpoints requiring date ranges (throughput, cumulative flow)
export interface DateRangeMetricsParams extends BaseMetricsParams {
  start_date: string
  end_date: string
}

// Parameters for endpoints with optional date filters (cycle time, lead time)
export interface OptionalDateMetricsParams extends BaseMetricsParams {
  start_date?: string
  end_date?: string
}

export interface ThroughputResponse {
  period: string
  throughput: number
  start_date: string
  end_date: string
}

export interface CycleTimeResponse {
  avg_cycle_time_hours: number
  project_id?: number
  start_date: string
  end_date: string
}

export interface LeadTimeResponse {
  avg_lead_time_hours: number
  project_id?: number
  start_date: string
  end_date: string
}

export interface WIPResponse {
  current_wip: number
  project_id?: number
  wip_limit?: number
}

export interface BlockedStoriesResponse {
  count: number
  stories: Array<{
    id: number
    title: string
    blocked_since: string
  }>
}

export const metricsAPI = {
  // Get throughput metrics (REQUIRES: project_id, start_date, end_date)
  async getThroughput(params: DateRangeMetricsParams): Promise<ThroughputResponse> {
    const response = await axiosInstance.get<ThroughputResponse>('/metrics/throughput', { params })
    return response.data
  },

  // Get average cycle time (REQUIRES: project_id; OPTIONAL: start_date, end_date)
  async getCycleTime(params: OptionalDateMetricsParams): Promise<CycleTimeResponse> {
    const response = await axiosInstance.get<CycleTimeResponse>('/metrics/cycle-time', { params })
    return response.data
  },

  // Get average lead time (REQUIRES: project_id; OPTIONAL: start_date, end_date)
  async getLeadTime(params: OptionalDateMetricsParams): Promise<LeadTimeResponse> {
    const response = await axiosInstance.get<LeadTimeResponse>('/metrics/lead-time', { params })
    return response.data
  },

  // Get current WIP (REQUIRES: project_id)
  async getWIP(params: BaseMetricsParams): Promise<WIPResponse> {
    const response = await axiosInstance.get<WIPResponse>('/metrics/wip', { params })
    return response.data
  },

  // Get cumulative flow diagram data (REQUIRES: project_id, start_date, end_date)
  async getCumulativeFlow(params: DateRangeMetricsParams): Promise<CumulativeFlowData[]> {
    const response = await axiosInstance.get<CumulativeFlowData[]>('/metrics/cumulative-flow', { params })
    return response.data
  },

  // Get blocked stories (REQUIRES: project_id)
  async getBlockedStories(params: BaseMetricsParams): Promise<BlockedStoriesResponse> {
    const response = await axiosInstance.get<BlockedStoriesResponse>('/metrics/blocked', { params })
    return response.data
  },
}
