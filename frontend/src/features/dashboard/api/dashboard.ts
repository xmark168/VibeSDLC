import axiosInstance from '@/core/lib/axios'
import type { DashboardData, DashboardMetrics, Activity } from '@/features/dashboard/types/dashboard'
import { projectsAPI } from '@/features/projects/api/projects'
import { metricsAPI } from '@/features/metrics/api/metrics'

// Helper function to format dates for API
const formatDate = (date: Date): string => {
  return date.toISOString()
}

// Helper function to calculate date range (last N days)
const getDateRange = (days: number = 30) => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)

  return {
    start_date: formatDate(startDate),
    end_date: formatDate(endDate),
  }
}

export const dashboardAPI = {
  // Get all dashboard data for a specific project
  async getDashboardData(projectId: number): Promise<DashboardData> {
    try {
      // Calculate date range (last 30 days)
      const dateRange = getDateRange(30)

      // Fetch all data in parallel for better performance
      const [
        projects,
        throughput,
        cycleTime,
        wip,
        blockedStories,
        cumulativeFlow,
      ] = await Promise.all([
        projectsAPI.getProjects(),
        metricsAPI.getThroughput({
          project_id: projectId,
          ...dateRange,
        }),
        metricsAPI.getCycleTime({
          project_id: projectId,
          ...dateRange,
        }),
        metricsAPI.getWIP({
          project_id: projectId,
        }),
        metricsAPI.getBlockedStories({
          project_id: projectId,
        }),
        metricsAPI.getCumulativeFlow({
          project_id: projectId,
          ...dateRange,
        }),
      ])

      // Calculate active stories count
      const activeStories = wip.current_wip || 0

      // Aggregate metrics
      const metrics: DashboardMetrics = {
        totalProjects: projects.length,
        activeStories,
        throughput: throughput.throughput || 0,
        avgCycleTime: cycleTime.avg_cycle_time_hours || 0,
        wip: activeStories,
        blockedStories: blockedStories.count || 0,
      }

      // Mock recent activities (in a real app, this would come from backend)
      const recentActivities: Activity[] = []

      // Mock throughput and cycle time data (for charts)
      const throughputData = []
      const cycleTimeData = []

      return {
        metrics,
        projects,
        recentActivities,
        cumulativeFlow,
        throughput: throughputData,
        cycleTime: cycleTimeData,
      }
    } catch (error) {
      throw error
    }
  },

  // Get dashboard data for all projects (aggregated view)
  async getAllProjectsData(): Promise<DashboardData> {
    try {
      const projects = await projectsAPI.getProjects()

      if (projects.length === 0) {
        // Return empty dashboard data
        return {
          metrics: {
            totalProjects: 0,
            activeStories: 0,
            throughput: 0,
            avgCycleTime: 0,
            wip: 0,
            blockedStories: 0,
          },
          projects: [],
          recentActivities: [],
          cumulativeFlow: [],
          throughput: [],
          cycleTime: [],
        }
      }

      // If user has projects, fetch data for the first project
      return this.getDashboardData(projects[0].id)
    } catch (error) {
      throw error
    }
  },

  // Get recent activities (placeholder for now)
  async getRecentActivities(): Promise<Activity[]> {
    // TODO: Implement when backend endpoint is available
    return []
  },
}
