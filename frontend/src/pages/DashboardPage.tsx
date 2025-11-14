import { useEffect, useState } from 'react'
import { TrendingUp, FolderKanban, ListTodo, Clock, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { dashboardAPI } from '@/features/dashboard/api/dashboard'
import type { DashboardData } from '@/features/dashboard/types/dashboard'
import { Skeleton } from '@/components/ui/skeleton.jsx'
import { Button } from '@/shared/ui/button'
import { ROUTES } from '@/core/constants/routes'

export const DashboardPage = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true)
        setError(null)
        // Use getAllProjectsData which handles no-projects case
        const data = await dashboardAPI.getAllProjectsData()
        setDashboardData(data)
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to load dashboard data'
        setError(errorMessage)
      } finally {
        setIsLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-8 fade-in">
        <div className="space-y-3">
          <Skeleton className="h-12 w-80 glass-premium" />
          <Skeleton className="h-6 w-96 glass" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-40 glass-premium animate-pulse" />
          ))}
        </div>
        <Skeleton className="h-64 w-full glass-premium" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="fade-in">
        <div className="glass-premium p-12 text-center space-y-6">
          <div className="flex justify-center">
            <div className="p-6 bg-gradient-to-br from-red-500/20 to-orange-500/20 rounded-full backdrop-blur-xl">
              <svg className="h-16 w-16 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-red-600">Oops! Something went wrong</h2>
            <p className="text-lg font-medium text-foreground">{error}</p>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Please check your backend connection and try again. If the problem persists, contact support.
            </p>
          </div>
          <Button
            onClick={() => window.location.reload()}
            size="lg"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg hover:shadow-2xl transition-all duration-300"
          >
            <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Page
          </Button>
        </div>
      </div>
    )
  }

  const metrics = dashboardData?.metrics
  const hasProjects = dashboardData?.projects && dashboardData.projects.length > 0

  // If no projects, show empty state
  if (!hasProjects) {
    return (
      <div className="space-y-8 fade-in">
        {/* Page Header */}
        <div className="space-y-3">
          <h1 className="text-5xl font-bold gradient-text">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-lg">
            Welcome! Create your first project to get started.
          </p>
        </div>

        {/* Empty State */}
        <div className="glass-premium p-16 text-center space-y-8 shine">
          <div className="flex justify-center">
            <div className="relative">
              {/* Animated background circles */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-purple-600/20 rounded-full blur-3xl animate-pulse"></div>
              <div className="relative p-8 bg-gradient-to-br from-blue-500/10 to-purple-600/10 rounded-full backdrop-blur-xl">
                <FolderKanban className="h-24 w-24 text-blue-600" />
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              No Projects Yet
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
              Start your journey by creating your first project. You'll be able to manage stories,
              track metrics, visualize your workflow, and much more.
            </p>
            <div className="flex flex-wrap gap-4 justify-center pt-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <ListTodo className="h-4 w-4 text-blue-600" />
                </div>
                <span>Story Management</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <TrendingUp className="h-4 w-4 text-purple-600" />
                </div>
                <span>Metrics & Analytics</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="p-2 bg-pink-500/10 rounded-lg">
                  <Clock className="h-4 w-4 text-pink-600" />
                </div>
                <span>Time Tracking</span>
              </div>
            </div>
          </div>
          <Button
            onClick={() => navigate(ROUTES.PROJECTS)}
            size="lg"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-xl hover:shadow-2xl transition-all duration-500 hover:scale-105 text-lg px-8 py-6"
          >
            <Plus className="h-6 w-6 mr-2" />
            Create Your First Project
          </Button>
        </div>
      </div>
    )
  }

  const metricCards = [
    {
      title: 'Total Projects',
      value: metrics?.totalProjects || 0,
      icon: FolderKanban,
      trend: '+12%',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      title: 'Active Stories',
      value: metrics?.activeStories || 0,
      icon: ListTodo,
      trend: '+5%',
      color: 'from-purple-500 to-pink-500',
    },
    {
      title: 'Throughput',
      value: `${metrics?.throughput || 0}/week`,
      icon: TrendingUp,
      trend: '+8%',
      color: 'from-green-500 to-emerald-500',
    },
    {
      title: 'Avg Cycle Time',
      value: `${Math.round(metrics?.avgCycleTime || 0)}h`,
      icon: Clock,
      trend: '-15%',
      color: 'from-orange-500 to-red-500',
    },
  ]

  return (
    <div className="space-y-10">
      {/* Page Header */}
      <div className="space-y-3 fade-in">
        <h1 className="text-5xl font-bold gradient-text">
          Dashboard
        </h1>
        <p className="text-muted-foreground text-lg">
          Welcome back! Here's an overview of your projects and metrics.
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricCards.map((card, index) => {
          const Icon = card.icon
          const delayClass = `fade-in-delay-${index + 1}` as any
          return (
            <div
              key={card.title}
              className={`glass-premium group hover:scale-105 transition-all duration-500 cursor-pointer relative overflow-hidden ${delayClass}`}
            >
              {/* Gradient overlay on hover */}
              <div className={`absolute inset-0 bg-gradient-to-br ${card.color} opacity-0 group-hover:opacity-10 transition-opacity duration-500`}></div>

              <div className="relative p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                      {card.title}
                    </p>
                    <p className="text-4xl font-bold bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
                      {card.value}
                    </p>
                  </div>
                  <div
                    className={`p-4 rounded-2xl bg-gradient-to-br ${card.color} shadow-lg group-hover:shadow-2xl group-hover:scale-110 transition-all duration-500`}
                  >
                    <Icon className="h-7 w-7 text-white" />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${card.trend.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                    {card.trend}
                  </span>
                  <span className="text-xs text-muted-foreground">from last week</span>
                </div>
              </div>

              {/* Shine effect border */}
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            </div>
          )
        })}
      </div>

      {/* Projects Section */}
      <div className="glass-premium p-8 fade-in-delay-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              Active Projects
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Your ongoing projects and their progress
            </p>
          </div>
          <button
            onClick={() => navigate(ROUTES.PROJECTS)}
            className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500/10 to-purple-600/10 hover:from-blue-500/20 hover:to-purple-600/20 transition-all duration-300"
          >
            <span className="text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              View all
            </span>
            <svg className="h-4 w-4 text-blue-600 group-hover:translate-x-1 transition-transform duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboardData.projects.slice(0, 6).map((project, index) => (
            <div
              key={project.id}
              className="group glass-card hover:scale-105 transition-all duration-500 cursor-pointer relative overflow-hidden shine"
              onClick={() => navigate(`${ROUTES.PROJECTS}/${project.id}`)}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {/* Gradient border effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl"></div>

              <div className="relative p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-bold text-xl text-foreground group-hover:text-blue-600 transition-colors duration-300 mb-2">
                      {project.name}
                    </h3>
                    <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                      {project.description || 'No description'}
                    </p>
                  </div>
                  <div className="p-2 bg-gradient-to-br from-blue-500/10 to-purple-600/10 rounded-lg">
                    <FolderKanban className="h-5 w-5 text-blue-600" />
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent font-bold">
                      {Math.round(project.progress || 0)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-1000 ease-out"
                      style={{ width: `${project.progress || 0}%` }}
                    ></div>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center justify-between pt-2 border-t border-white/10">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-500/10 rounded-lg">
                      <ListTodo className="h-3.5 w-3.5 text-blue-600" />
                    </div>
                    <span className="text-xs font-medium text-muted-foreground">
                      {project.active_stories_count || 0} active stories
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {project.active_stories_count === 0 ? (
                      <span className="text-yellow-600 font-medium">No active work</span>
                    ) : project.progress >= 80 ? (
                      <span className="text-green-600 font-medium">Almost done!</span>
                    ) : project.progress >= 50 ? (
                      <span className="text-blue-600 font-medium">In progress</span>
                    ) : (
                      <span className="text-purple-600 font-medium">Getting started</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
