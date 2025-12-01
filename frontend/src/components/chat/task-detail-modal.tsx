
import { Download, Zap, User, Users, Flag, Calendar, ChevronRight, MessageSquare, FileText, ScrollText, Send, Paperclip, Smile } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { KanbanCardData } from "./kanban-card"
import { useState, useRef, useEffect } from "react"

interface TaskDetailModalProps {
  card: KanbanCardData | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadResult: (card: KanbanCardData) => void
}

// Mock chat messages type
interface ChatMessage {
  id: string
  author: string
  author_type: 'user' | 'agent'
  content: string
  timestamp: string
  avatar?: string
}

export function TaskDetailModal({ card, open, onOpenChange, onDownloadResult }: TaskDetailModalProps) {
  const [selectedChild, setSelectedChild] = useState<KanbanCardData | null>(null)
  const [activeTab, setActiveTab] = useState<string>("detail")
  const [chatMessage, setChatMessage] = useState("")
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      author: 'John Doe',
      author_type: 'user',
      content: 'Chúng ta cần làm rõ acceptance criteria cho story này.',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: '2',
      author: 'Product Owner Agent',
      author_type: 'agent',
      content: 'Tôi đã cập nhật acceptance criteria. Các điểm chính:\n1. User có thể login bằng email/password\n2. Hiển thị error message khi sai thông tin\n3. Redirect về dashboard sau khi login thành công',
      timestamp: new Date(Date.now() - 3000000).toISOString(),
    },
    {
      id: '3',
      author: 'Jane Smith',
      author_type: 'user',
      content: 'Cảm ơn! Story point 5 có hợp lý không?',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
    },
  ])
  const chatScrollRef = useRef<HTMLDivElement>(null)

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatScrollRef.current && activeTab === 'chat') {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [chatMessages, activeTab])

  if (!card) return null

  const handleSendMessage = () => {
    if (!chatMessage.trim()) return

    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      author: 'Current User',
      author_type: 'user',
      content: chatMessage,
      timestamp: new Date().toISOString(),
    }

    setChatMessages(prev => [...prev, newMessage])
    setChatMessage("")
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Vừa xong'
    if (diffMins < 60) return `${diffMins} phút trước`
    if (diffHours < 24) return `${diffHours} giờ trước`
    if (diffDays < 7) return `${diffDays} ngày trước`

    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Get type badge color - Lean Kanban: UserStory, EnablerStory on board; Epic as parent
  const getTypeBadgeColor = (type?: string) => {
    switch (type) {
      case "Epic":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "UserStory":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "EnablerStory":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  // Format type name for display (UserStory -> User Story)
  const formatTypeName = (type?: string) => {
    if (!type) return ""
    switch (type) {
      case "UserStory":
        return "User Story"
      case "EnablerStory":
        return "Enabler Story"
      case "Epic":
        return "Epic"
      default:
        return type
    }
  }

  // Get status badge color
  const getStatusBadgeColor = (status?: string) => {
    switch (status) {
      case "Backlog":
        return "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20"
      case "Todo":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
      case "Doing":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
      case "Done":
        return "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {card.type && (
                  <Badge variant="outline" className={getTypeBadgeColor(card.type)}>
                    {formatTypeName(card.type)}
                  </Badge>
                )}
                {card.status && (
                  <Badge variant="outline" className={getStatusBadgeColor(card.status)}>
                    {card.status}
                  </Badge>
                )}
                {card.rank !== undefined && card.rank !== null && (
                  <Badge
                    variant="outline"
                    className={`gap-1 ${card.rank <= 3
                        ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
                        : card.rank <= 7
                          ? "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
                          : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                      }`}
                  >
                    <Flag className="w-3 h-3" />
                    Thứ tự: {card.rank}
                  </Badge>
                )}
              </div>
              <div className="text-base font-semibold text-foreground">{card.content}</div>
              <div className="text-xs text-muted-foreground font-normal mt-1">
                ID: {card.taskId?.slice(0, 8) || 'N/A'}
              </div>
            </div>
          </DialogTitle>
        </DialogHeader>

        <Separator />

        {/* Tabs Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="detail" className="gap-2">
              <FileText className="w-4 h-4" />
              Detail
            </TabsTrigger>
            <TabsTrigger value="chat" className="gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat
            </TabsTrigger>
            <TabsTrigger value="logs" className="gap-2">
              <ScrollText className="w-4 h-4" />
              Logs
            </TabsTrigger>
          </TabsList>

          {/* Detail Tab */}
          <TabsContent value="detail" className="flex-1 overflow-y-auto mt-4">
            <div className="space-y-4 text-sm">
          {/* Description */}
          {card.description && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Mô tả</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{card.description}</p>
            </div>
          )}

          {/* Requirements */}
          {card.requirements && card.requirements.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Requirements</h4>
              <ul className="space-y-1">
                {card.requirements.map((req: string, idx: number) => (
                  <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                    <span className="text-xs font-semibold text-muted-foreground mt-0.5">{idx + 1}.</span>
                    <span>{req}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Acceptance Criteria */}
          {card.acceptance_criteria && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Acceptance Criteria</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{card.acceptance_criteria}</p>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Story Points / Estimate */}
            {(card.story_point !== undefined && card.story_point !== null) && (
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Story Points</div>
                  <div className="text-sm font-medium">{card.story_point} SP</div>
                </div>
              </div>
            )}

            {(card.priority !== undefined && card.priority !== null) && (
              <div className="flex items-center gap-2">
                <Flag className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Priority</div>
                  <div className="text-sm font-medium">
                    {card.priority === 1 ? 'High' : 
                     card.priority === 2 ? 'Medium' : 'Low'}
                  </div>
                </div>
              </div>
            )}

            {/* Assignee */}
            {card.assignee_id && (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người thực hiện</div>
                  <div className="text-sm font-medium font-mono">
                    {card.assignee_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {card.type === "EnablerStory" ? "Developer/Infrastructure" : "Developer"}
                  </div>
                </div>
              </div>
            )}

            {/* Reviewer */}
            {card.reviewer_id && (
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Người review</div>
                  <div className="text-sm font-medium font-mono">
                    {card.reviewer_id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground">Tester</div>
                </div>
              </div>
            )}

            {/* Rank */}
            {(card.rank !== undefined && card.rank !== null) && (
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Rank</div>
                  <div className="text-sm font-medium">{card.rank}</div>
                </div>
              </div>
            )}

            {/* Epic ID */}
            {card.epic_id && (
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Epic ID</div>
                  <div className="text-sm font-medium font-mono">{card.epic_id.slice(0, 8)}</div>
                </div>
              </div>
            )}

            {/* Created at */}
            {card.created_at && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Ngày tạo</div>
                  <div className="text-sm font-medium">
                    {new Date(card.created_at).toLocaleDateString('vi-VN')}
                  </div>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* TraDS ============= Kanban Hierarchy: Parent Epic Display */}
          {card.parent && card.parent.type === "Epic" && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Epic</h4>
              <div className="flex items-center gap-2 p-2 rounded border border-border bg-muted/50">
                <Badge variant="outline" className={getTypeBadgeColor(card.parent.type)}>
                  {formatTypeName(card.parent.type)}
                </Badge>
                <span className="text-sm flex-1">{card.parent.content || card.parent.title}</span>
              </div>
            </div>
          )}

          {/* TraDS ============= Kanban Hierarchy: Children Display */}
          {card.children && card.children.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">
                Công việc con ({card.children.length})
              </h4>
              <div className="space-y-2">
                {card.children.map((child) => (
                  <div
                    key={child.id}
                    onClick={() => setSelectedChild(child)}
                    className="flex items-center gap-2 p-2 rounded border border-border hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Badge variant="outline" className={getTypeBadgeColor(child.type)}>
                      {formatTypeName(child.type)}
                    </Badge>
                    <span className="text-sm flex-1">{child.content || child.title}</span>
                    {child.status && (
                      <Badge variant="outline" className={getStatusBadgeColor(child.status)}>
                        {child.status}
                      </Badge>
                    )}
                    {child.story_point !== undefined && child.story_point !== null && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Zap className="w-3 h-3" />
                        {child.story_point} SP
                      </div>
                    )}
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent Info (Legacy) */}
          {card.agentName && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Agent đã xử lý</h4>
              <div className="flex items-center gap-2">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={card.agentAvatar || "/placeholder.svg"} alt={card.agentName} />
                  <AvatarFallback className="bg-primary/10 text-primary text-xs">
                    {card.agentName?.charAt(0) || "A"}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{card.agentName}</span>
              </div>
            </div>
          )}

          {/* Branch */}
          {card.branch && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Branch</h4>
              <code className="text-xs bg-muted px-2 py-1 rounded">{card.branch}</code>
            </div>
          )}

          {/* Subtasks */}
          {card.subtasks && card.subtasks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-2">Subtasks</h4>
              <ul className="space-y-1">
                {card.subtasks.map((subtask, index) => (
                  <li key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                    {subtask}
                  </li>
                ))}
              </ul>
            </div>
          )}

              {/* Result */}
              {card.result && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-foreground">Kết quả</h4>
                    <Button size="sm" variant="outline" onClick={() => onDownloadResult(card)} className="h-7 text-xs">
                      <Download className="w-3 h-3 mr-1" />
                      Tải xuống .md
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground bg-muted p-3 rounded max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">{card.result}</pre>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="flex-1 flex flex-col mt-4 h-[500px]">
            {/* Chat Header */}
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold">Story Discussion</h3>
                <Badge variant="outline" className="text-xs">
                  {chatMessages.length} messages
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                Real-time collaboration
              </div>
            </div>

            {/* Messages Area */}
            <div
              ref={chatScrollRef}
              className="flex-1 overflow-y-auto py-4 space-y-4"
            >
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-start gap-3 ${
                    msg.author_type === 'user' ? 'flex-row' : 'flex-row'
                  }`}
                >
                  {/* Avatar */}
                  <Avatar className="w-8 h-8 shrink-0">
                    {msg.author_type === 'agent' ? (
                      <AvatarFallback className="bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs">
                        🤖
                      </AvatarFallback>
                    ) : (
                      <AvatarFallback className="bg-primary/10 text-primary text-xs">
                        {msg.author.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    )}
                  </Avatar>

                  {/* Message Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-xs font-semibold text-foreground">
                        {msg.author}
                      </span>
                      {msg.author_type === 'agent' && (
                        <Badge variant="outline" className="text-[10px] h-4 px-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                          Agent
                        </Badge>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        {formatTimestamp(msg.timestamp)}
                      </span>
                    </div>
                    <div className={`
                      text-sm rounded-lg px-3 py-2 inline-block max-w-full
                      ${msg.author_type === 'agent'
                        ? 'bg-blue-500/10 text-foreground border border-blue-500/20'
                        : 'bg-muted text-foreground'
                      }
                    `}>
                      <p className="whitespace-pre-wrap wrap-break-word">{msg.content}</p>
                    </div>
                  </div>
                </div>
              ))}

              {/* Empty State */}
              {chatMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-12">
                  <MessageSquare className="w-12 h-12 mb-3 opacity-30" />
                  <p className="text-sm font-medium">No messages yet</p>
                  <p className="text-xs mt-1">Start the conversation about this story</p>
                </div>
              )}
            </div>

            {/* Message Input */}
            <div className="pt-3 border-t">
              <div className="flex items-end gap-2">
                <div className="flex-1 relative">
                  <Textarea
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type a message... (Shift+Enter for new line)"
                    className="min-h-[60px] max-h-[120px] resize-none pr-20 text-sm"
                  />
                  <div className="absolute right-2 bottom-2 flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 hover:bg-muted"
                    >
                      <Paperclip className="w-4 h-4 text-muted-foreground" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 hover:bg-muted"
                    >
                      <Smile className="w-4 h-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!chatMessage.trim()}
                  size="sm"
                  className="h-[60px] px-4"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-[10px] text-muted-foreground mt-1.5">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="flex-1 overflow-y-auto mt-4">
            <div className="space-y-4">
              <div className="text-center text-muted-foreground py-8">
                <ScrollText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Activity logs coming soon...</p>
                <p className="text-xs mt-1">View all activities and changes for this story</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>

      {/* TraDS ============= Kanban Hierarchy: Nested dialog for viewing child items */}
      {selectedChild && (
        <TaskDetailModal
          card={selectedChild}
          open={!!selectedChild}
          onOpenChange={() => setSelectedChild(null)}
          onDownloadResult={onDownloadResult}
        />
      )}
    </Dialog>
  )
}
