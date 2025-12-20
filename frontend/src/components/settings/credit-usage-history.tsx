import { useState } from "react"
import { useCreditActivities } from "@/queries/credits"
import { formatDistanceToNow } from "date-fns"
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
import { ChevronLeft, ChevronRight, TrendingDown, Cpu, Zap, Bot } from "lucide-react"

const ITEMS_PER_PAGE = 20

export function CreditUsageHistory() {
  const [currentPage, setCurrentPage] = useState(1)
  
  const { data, isLoading } = useCreditActivities({
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
  })
  
  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 0
  
  const formatReason = (reason: string) => {
    if (reason.startsWith('llm_tokens_')) {
      return 'LLM Usage'
    }
    return reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }
  
  const formatAmount = (amount: number) => {
    if (amount < 0) {
      return <span className="text-red-500">-{Math.abs(amount)}</span>
    }
    return <span className="text-green-500">+{amount}</span>
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-96" />
          </CardHeader>
          <CardContent className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    )
  }
  
  if (!data) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Failed to load credit usage history
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-red-500" />
              Total Spent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.summary.total_credits_spent}</div>
            <p className="text-xs text-muted-foreground">credits</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-500" />
              Tokens Used
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.summary.total_tokens_used.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">tokens</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-500" />
              LLM Calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.summary.total_llm_calls}</div>
            <p className="text-xs text-muted-foreground">API calls</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Bot className="w-4 h-4 text-purple-500" />
              Top Agent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold truncate">
              {data.summary.top_agent || 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">most active</p>
          </CardContent>
        </Card>
      </div>

      {/* Activity Table */}
      <Card>
        <CardHeader>
          <CardTitle>Credit Usage History</CardTitle>
          <CardDescription>
            View your detailed credit and token usage across all activities
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No credit activities yet
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Agent</TableHead>
                      <TableHead>Project</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead className="text-right">Tokens</TableHead>
                      <TableHead className="text-right">Credits</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((activity) => (
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
                        <TableCell className="text-sm">
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
                        <TableCell className="text-right text-sm font-semibold">
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
                    {Math.min(currentPage * ITEMS_PER_PAGE, data.total)} of {data.total} activities
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
  )
}
