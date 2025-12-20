import { useState, useEffect } from "react"
import { useCurrentSubscription } from "@/queries/subscription"
import { useCreditActivities } from "@/queries/credits"
import { useProjectTokenBudget } from "@/queries/projects"
import { formatDistanceToNow } from "date-fns"
import { useQueryClient } from "@tanstack/react-query"
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { 
  ChevronLeft, 
  ChevronRight, 
  TrendingDown, 
  Cpu, 
  Zap, 
  Bot, 
  Coins,
  Search,
  RefreshCcw,
  Calendar,
  CalendarDays,
  AlertCircle
} from "lucide-react"
import { Progress } from "@/components/ui/progress"

const ITEMS_PER_PAGE = 15

interface TokenBudgetData {
  daily: {
    limit: number
    used: number
    remaining: number
    usage_percentage: number
  }
  monthly: {
    limit: number
    used: number
    remaining: number
    usage_percentage: number
  }
}

interface TokenUsagePanelProps {
  projectId?: string
}

export function TokenUsagePanel({ projectId }: TokenUsagePanelProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState("")
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [filterByProject, setFilterByProject] = useState(false)
  
  const queryClient = useQueryClient()
  
  // Fetch subscription data for credit balance
  const { data: subscriptionData, isLoading: subLoading, refetch: refetchSubscription } = useCurrentSubscription()
  
  // Fetch credit activities (optionally filtered by project)
  const { data: activitiesData, isLoading: activitiesLoading, error: activitiesError, refetch: refetchActivities } = useCreditActivities({
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
    project_id: filterByProject ? projectId : undefined,
  })
  
  // Fetch token budget for project
  const { data: tokenBudget, isLoading: budgetLoading, error: budgetError, refetch: refetchBudget } = useProjectTokenBudget(projectId) as {
    data: TokenBudgetData | null | undefined
    isLoading: boolean
    error: Error | null
    refetch: () => void
  }
  
  // Debug: Log token budget data
  useEffect(() => {
    if (projectId) {
      console.log('[TokenUsagePanel] projectId:', projectId)
      console.log('[TokenUsagePanel] tokenBudget:', tokenBudget)
      console.log('[TokenUsagePanel] budgetLoading:', budgetLoading)
      console.log('[TokenUsagePanel] budgetError:', budgetError)
    }
  }, [projectId, tokenBudget, budgetLoading, budgetError])
  
  // Debug: Log activities data
  useEffect(() => {
    console.log('[TokenUsagePanel] Usage History Debug:', {
      projectId,
      filterByProject,
      activitiesData,
      isLoading: activitiesLoading,
      error: activitiesError,
      itemsCount: activitiesData?.items?.length,
      total: activitiesData?.total
    })
  }, [projectId, filterByProject, activitiesData, activitiesLoading, activitiesError])
  
  // Reset page to 1 when filter changes
  useEffect(() => {
    setCurrentPage(1)
  }, [filterByProject, searchQuery])
  
  // Listen for agent responses to refetch data
  useEffect(() => {
    const handleAgentFinish = (event: CustomEvent) => {
      console.log('[TokenUsagePanel] Agent finished, refetching all data...', event.detail)
      
      // Invalidate all queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['subscription'] })
      queryClient.invalidateQueries({ queryKey: ['credits'] })
      queryClient.invalidateQueries({ queryKey: ['project-token-budget'] })
      
      // Update last update timestamp
      setLastUpdate(new Date())
    }
    
    // Listen to custom event dispatched by chat WebSocket
    window.addEventListener('agent_response_complete', handleAgentFinish as EventListener)
    
    return () => {
      window.removeEventListener('agent_response_complete', handleAgentFinish as EventListener)
    }
  }, [queryClient])
  
  // Calculate total credits
  const subRemainingCredits = subscriptionData?.credit_wallet?.remaining_credits || 0
  const purchasedRemainingCredits = subscriptionData?.purchased_wallet?.remaining_credits || 0
  const totalRemainingCredits = subRemainingCredits + purchasedRemainingCredits
  
  const subTotalCredits = subscriptionData?.credit_wallet?.total_credits || 0
  const purchasedTotalCredits = subscriptionData?.purchased_wallet?.total_credits || 0
  const totalCredits = subTotalCredits + purchasedTotalCredits
  
  const creditPercentage = totalCredits > 0 ? (totalRemainingCredits / totalCredits) * 100 : 0
  
  const totalPages = activitiesData ? Math.ceil(activitiesData.total / ITEMS_PER_PAGE) : 0
  
  const formatReason = (reason: string) => {
    if (reason.startsWith('llm_tokens_')) {
      return 'LLM Usage'
    }
    return reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }
  
  const formatAmount = (amount: number) => {
    if (amount < 0) {
      return <span className="text-red-500 font-semibold">-{Math.abs(amount)}</span>
    }
    return <span className="text-green-500 font-semibold">+{amount}</span>
  }

  // Filter activities based on search query
  const filteredActivities = activitiesData?.items.filter(activity => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      activity.agent_name?.toLowerCase().includes(query) ||
      activity.project_name?.toLowerCase().includes(query) ||
      activity.reason?.toLowerCase().includes(query) ||
      activity.model_used?.toLowerCase().includes(query)
    )
  }) || []

  const handleRefresh = () => {
    refetchSubscription()
    refetchActivities()
    refetchBudget()
  }
  
  // Listen for real-time credit updates via WebSocket
  useEffect(() => {
    const handleCreditUpdate = (event: CustomEvent) => {
      setLastUpdate(new Date())
      refetchSubscription()
      refetchActivities()
    }
    
    window.addEventListener('credit_updated', handleCreditUpdate as EventListener)
    return () => window.removeEventListener('credit_updated', handleCreditUpdate as EventListener)
  }, [refetchSubscription, refetchActivities])

  if (subLoading && activitiesLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-background overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Header with Refresh */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-foreground">Token Usage</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor your credit balance and usage history
              {lastUpdate && (
                <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                  • Updated {formatDistanceToNow(lastUpdate, { addSuffix: true })}
                </span>
              )}
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh}
            className="gap-2"
          >
            <RefreshCcw className="w-4 h-4" />
            Refresh
          </Button>
        </div>

        {/* Token Budget Cards (only show if projectId is provided) */}
        {projectId && (
          budgetLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
            </div>
          ) : budgetError ? (
            <Card className="border-red-500/20">
              <CardContent className="pt-6">
                <div className="flex flex-col items-center gap-2">
                  <AlertCircle className="w-8 h-8 text-red-500" />
                  <p className="text-sm text-red-600 dark:text-red-400 font-medium">Failed to load token budget</p>
                  <p className="text-xs text-muted-foreground">{(budgetError as Error)?.message || 'Unknown error'}</p>
                  <Button size="sm" onClick={() => refetchBudget()}>
                    <RefreshCcw className="w-4 h-4 mr-2" />
                    Retry
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : tokenBudget ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Daily Token Budget */}
            <Card className="border-2 border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-transparent">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  Daily Token Budget
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-gray-900 dark:text-foreground">
                      {tokenBudget.daily.remaining.toLocaleString()}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      / {tokenBudget.daily.limit.toLocaleString()}
                    </span>
                  </div>
                  <Progress 
                    value={100 - tokenBudget.daily.usage_percentage} 
                    className="h-2"
                  />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{(100 - tokenBudget.daily.usage_percentage).toFixed(1)}% remaining</span>
                    <span>Resets at midnight UTC</span>
                  </div>
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Used today: {tokenBudget.daily.used.toLocaleString()} tokens ({tokenBudget.daily.usage_percentage.toFixed(1)}%)
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Monthly Token Budget */}
            <Card className="border-2 border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                  <CalendarDays className="w-5 h-5 text-purple-500" />
                  Monthly Token Budget
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-gray-900 dark:text-foreground">
                      {tokenBudget.monthly.remaining.toLocaleString()}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      / {tokenBudget.monthly.limit.toLocaleString()}
                    </span>
                  </div>
                  <Progress 
                    value={100 - tokenBudget.monthly.usage_percentage} 
                    className="h-2"
                  />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{(100 - tokenBudget.monthly.usage_percentage).toFixed(1)}% remaining</span>
                    <span>Resets on 1st of month</span>
                  </div>
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Used this month: {tokenBudget.monthly.used.toLocaleString()} tokens ({tokenBudget.monthly.usage_percentage.toFixed(1)}%)
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          ) : (
            <Card className="border-yellow-500/20">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground text-center">
                  Failed to load token budget. Click refresh to retry.
                </p>
              </CardContent>
            </Card>
          )
        )}

        {/* Credit Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Total Credits Card */}
          <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                <Coins className="w-5 h-5 text-primary" />
                Total Credits Remaining
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold text-gray-900 dark:text-foreground">
                    {totalRemainingCredits.toLocaleString()}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    / {totalCredits.toLocaleString()}
                  </span>
                </div>
                <Progress value={creditPercentage} className="h-2" />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{creditPercentage.toFixed(1)}% remaining</span>
                  {subscriptionData?.credit_wallet?.period_end && (
                    <span>Renews: {new Date(subscriptionData.credit_wallet.period_end).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Breakdown Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Credit Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Subscription Credits */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20">
                  <div>
                    <p className="text-xs text-muted-foreground">Plan Credits</p>
                    <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                      {subRemainingCredits.toLocaleString()}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    Subscription
                  </Badge>
                </div>

                {/* Purchased Credits */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-purple-50 dark:bg-purple-950/20">
                  <div>
                    <p className="text-xs text-muted-foreground">Purchased Credits</p>
                    <p className="text-lg font-semibold text-purple-600 dark:text-purple-400">
                      {purchasedRemainingCredits.toLocaleString()}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    Permanent
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Usage Summary Statistics */}
        {activitiesLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16 mb-2" />
                  <Skeleton className="h-3 w-12" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : activitiesData && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-2 text-muted-foreground">
                  <TrendingDown className="w-4 h-4 text-red-500" />
                  Total Spent
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{activitiesData.summary.total_credits_spent}</div>
                <p className="text-xs text-muted-foreground">credits</p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-2 text-muted-foreground">
                  <Cpu className="w-4 h-4 text-blue-500" />
                  Tokens Used
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(activitiesData.summary.total_tokens_used / 1000).toFixed(1)}K
                </div>
                <p className="text-xs text-muted-foreground">tokens</p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-2 text-muted-foreground">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  LLM Calls
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{activitiesData.summary.total_llm_calls}</div>
                <p className="text-xs text-muted-foreground">API calls</p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-2 text-muted-foreground">
                  <Bot className="w-4 h-4 text-purple-500" />
                  Top Agent
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold truncate">
                  {activitiesData.summary.top_agent || 'N/A'}
                </div>
                <p className="text-xs text-muted-foreground">most active</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Activity History */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Usage History</CardTitle>
                <CardDescription>
                  Detailed breakdown of your credit and token usage
                </CardDescription>
              </div>
              <div className="flex items-center gap-3">
                {projectId && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50">
                    <span className="text-xs text-muted-foreground whitespace-nowrap">This project only</span>
                    <Switch
                      checked={filterByProject}
                      onCheckedChange={setFilterByProject}
                      className="scale-75"
                    />
                  </div>
                )}
                <div className="relative w-64">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search activities..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 h-9"
                  />
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {activitiesLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : activitiesError ? (
              <Card className="border-red-500/20">
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center gap-2">
                    <AlertCircle className="w-8 h-8 text-red-500" />
                    <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                      Failed to load usage history
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(activitiesError as Error)?.message || 'Unknown error'}
                    </p>
                    <Button size="sm" onClick={() => refetchActivities()}>
                      <RefreshCcw className="w-4 h-4 mr-2" />
                      Retry
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : filteredActivities.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Coins className="w-12 h-12 mx-auto mb-3 opacity-40" />
                {!searchQuery ? (
                  <>
                    <p className="font-medium">No credit activities yet</p>
                    <p className="text-sm mt-2">
                      Start chatting with agents to see your usage history here
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium">No activities match "{searchQuery}"</p>
                    <p className="text-sm mt-2">Try a different search term</p>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Project</TableHead>
                        <TableHead>Model</TableHead>
                        <TableHead className="text-right">Tokens</TableHead>
                        <TableHead className="text-right">Credits</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredActivities.map((activity) => (
                        <TableRow key={activity.id}>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="text-sm font-medium">{formatReason(activity.reason)}</span>
                              {activity.task_type && (
                                <Badge variant="outline" className="w-fit text-xs mt-1">
                                  {activity.task_type}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm">
                            {activity.agent_name || '-'}
                          </TableCell>
                          <TableCell className="text-sm truncate max-w-[150px]">
                            {activity.project_name || '-'}
                          </TableCell>
                          <TableCell>
                            {activity.model_used && (
                              <Badge variant="secondary" className="text-xs">
                                {activity.model_used.replace('claude-', '')}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right text-sm font-mono">
                            {activity.tokens_used ? activity.tokens_used.toLocaleString() : '-'}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {formatAmount(activity.amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                
                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-muted-foreground">
                      Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to{' '}
                      {Math.min(currentPage * ITEMS_PER_PAGE, activitiesData?.total || 0)} of {activitiesData?.total || 0} activities
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                      </Button>
                      <div className="text-sm">
                        Page {currentPage} of {totalPages}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                      >
                        Next
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
