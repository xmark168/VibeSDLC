import type React from "react";
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ChevronDown,
  ChevronUp,
  ArrowUp,
  Copy,
  Check,
  X,
  Moon,
  Sun,
  AtSign,
  PanelRightClose,
  PanelLeftClose,
  ChevronsLeft,
  Loader2,
} from "lucide-react";
import { TechStackDialog } from "./tech-stack-dialog";
import { useTheme } from "@/components/provider/theme-provider";
import { useChatWebSocket } from "@/hooks/useChatWebSocket";
import { useAuth } from "@/hooks/useAuth";
import { useMessages } from "@/queries/messages";
import { AuthorType, type Message } from "@/types/message";
import { AgentPreviewModal } from "./agent-preview-modal";
import { MessagePreviewCard } from "./MessagePreviewCard";
import { AgentStatusIndicator } from "./agent-status-indicator";

interface ChatPanelProps {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onCollapse: () => void;
  onSidebarHover: (hovered: boolean) => void;
  projectId?: string;
  onSendMessageReady?: (
    sendFn: (params: { content: string; author_type?: 'user' | 'agent' }) => boolean
  ) => void;
  onConnectionChange?: (connected: boolean) => void;
  onKanbanDataChange?: (data: any) => void;
  onActiveTabChange?: (tab: string | null) => void;
}

const AGENTS = [
  { name: "Mike", role: "Team Leader", avatar: "👨‍💼" },
  { name: "Emma", role: "Product Manager", avatar: "👩‍💼" },
  { name: "Bob", role: "Architect", avatar: "👨‍🔧" },
  { name: "Alex", role: "Engineer", avatar: "👨‍💻" },
  { name: "Developer", role: "Developer", avatar: "🔧" },
  { name: "Tester", role: "Tester", avatar: "🧪" },
];

export function ChatPanelWS({
  sidebarCollapsed,
  onToggleSidebar,
  onCollapse,
  onSidebarHover,
  projectId,
  onSendMessageReady,
  onConnectionChange,
  onKanbanDataChange,
  onActiveTabChange,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState("");
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(
    new Set()
  );
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mentionDropdownRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const prevMessagesLengthRef = useRef(0);

  // Get access token
  const token = localStorage.getItem("access_token");

  // Fetch existing messages
  const { data: messagesData } = useMessages({
    project_id: projectId || "",
    skip: 0,
    limit: 100,
  });

  // WebSocket connection
  const {
    isConnected,
    isReady,
    messages: wsMessages,
    typingAgents,
    agentStatus,
    pendingQuestions,
    pendingPreviews,
    kanbanData,
    activeTab,
    sendMessage: wsSendMessage,
    submitPreviewChoice,
    reopenPreview,
    closePreview,
  } = useChatWebSocket(projectId, token || undefined);

  // Derive agentProgress from agentStatus
  const agentProgress = {
    isExecuting: agentStatus.status === 'thinking' || agentStatus.status === 'acting'
  };

  // Combine existing messages with WebSocket messages
  const apiMessages = messagesData?.data || [];

  // Filter WebSocket messages:
  // 1. Keep all non-temp messages (agent responses via WebSocket)
  // 2. For temp messages, keep them unless API has the exact same message (by checking timestamp proximity)
  const filteredWsMessages = wsMessages.filter(wsMsg => {
    // Keep non-temp messages
    if (!wsMsg.id.startsWith('temp-')) return true;

    // For temp messages, check if API has a real message with same content AND close timestamp
    // This prevents filtering out new messages when user sends same content multiple times
    const tempTimestamp = new Date(wsMsg.created_at).getTime();
    const hasRealMessage = apiMessages.some(
      apiMsg => apiMsg.content === wsMsg.content &&
                apiMsg.author_type === wsMsg.author_type &&
                Math.abs(new Date(apiMsg.created_at).getTime() - tempTimestamp) < 5000 // Within 5 seconds
    );
    return !hasRealMessage;
  });

  // Combine and sort by timestamp
  const allMessages = [...apiMessages, ...filteredWsMessages].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  // Remove duplicates by id (keep first occurrence)
  const uniqueMessages = allMessages.filter(
    (msg, index, self) => index === self.findIndex((m) => m.id === msg.id)
  );

  // Notify parent when kanbanData changes
  useEffect(() => {
    if (kanbanData && onKanbanDataChange) {
      onKanbanDataChange(kanbanData);
    }
  }, [kanbanData, onKanbanDataChange]);

  // Notify parent when activeTab changes
  useEffect(() => {
    if (activeTab && onActiveTabChange) {
      onActiveTabChange(activeTab);
    }
  }, [activeTab, onActiveTabChange]);

  const toggleExpand = (id: string) => {
    setExpandedMessages((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const filteredAgents = AGENTS.filter((agent) =>
    agent.name.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  const insertMention = (agentName: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = message.slice(0, cursorPos);
    const textAfterCursor = message.slice(cursorPos);

    const atIndex = textBeforeCursor.lastIndexOf("@");
    const newText =
      textBeforeCursor.slice(0, atIndex) + `@${agentName} ` + textAfterCursor;

    setMessage(newText);
    setShowMentions(false);
    setMentionSearch("");

    setTimeout(() => {
      const newCursorPos = atIndex + agentName.length + 2;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
      textarea.focus();
    }, 0);
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);

    const atIndex = textBeforeCursor.lastIndexOf("@");
    const spaceAfterAt = textBeforeCursor.slice(atIndex).indexOf(" ");

    if (atIndex !== -1 && spaceAfterAt === -1 && cursorPos - atIndex <= 20) {
      const searchTerm = textBeforeCursor.slice(atIndex + 1);
      setMentionSearch(searchTerm);
      setShowMentions(true);
      setSelectedMentionIndex(0);
    } else {
      setShowMentions(false);
    }
  };

  const handleSend = () => {
    if (!message.trim()) return;
    if (!isReady) {
      console.error("WebSocket not ready");
      return;
    }

    let finalMessage = message.trim();

    // Send via WebSocket
    const success = wsSendMessage({
      content: finalMessage,
      author_type: "user",
    });

    if (success) {
      setMessage("");
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 0);
    }
  };

  // Reset waiting state when we receive agent messages or agent starts typing/processing
  useEffect(() => {
    if (wsMessages.length > 0) {
      const lastMessage = wsMessages[wsMessages.length - 1];
      if (lastMessage.author_type === AuthorType.AGENT) {
        setIsWaitingForResponse(false);
      }
    }
  }, [wsMessages]);

  useEffect(() => {
    if (typingAgents.length > 0 || agentProgress.isExecuting) {
      setIsWaitingForResponse(false);
    }
  }, [typingAgents, agentProgress.isExecuting]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentions && filteredAgents.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedMentionIndex((prev) => (prev + 1) % filteredAgents.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedMentionIndex(
          (prev) => (prev - 1 + filteredAgents.length) % filteredAgents.length
        );
      } else if (e.key === "Tab" || e.key === "Enter") {
        if (showMentions) {
          e.preventDefault();
          insertMention(filteredAgents[selectedMentionIndex].name);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        setShowMentions(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Handle edit message - reopen preview modal with existing data
  const handleEditMessage = (message: Message) => {
    if (!message.message_type || !message.structured_data) return

    // Convert Message to AgentPreview format
    const preview: any = {
      preview_id: `edit_${message.id}_${Date.now()}`, // New preview ID for edit
      preview_type: message.message_type,
      title: `Edit ${message.message_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`,
      prompt: 'You can edit or regenerate this preview',
      options: ['approve', 'edit', 'regenerate'],
    }

    // Add structured data based on type
    switch (message.message_type) {
      case 'product_brief':
        preview.brief = message.structured_data
        preview.incomplete_flag = message.metadata?.incomplete_flag
        break
      case 'product_vision':
        preview.vision = message.structured_data
        preview.quality_score = message.metadata?.quality_score
        preview.validation_result = message.metadata?.validation_result
        break
      case 'product_backlog':
        preview.backlog = message.structured_data
        break
    }

    // Reopen modal
    reopenPreview(preview)
  }

  const formatTimestamp = (dateStr: string) => {
    const date = new Date(dateStr);
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    const displayHours = hours % 12 || 12;
    const month = date.toLocaleString("en-US", { month: "short" });
    const day = date.getDate().toString().padStart(2, "0");
    return `${displayHours}:${minutes} ${ampm} on ${month} ${day}`;
  };

  const getAgentAvatar = (authorType: AuthorType) => {
    if (authorType === AuthorType.USER) return "👤";
    if (authorType === AuthorType.AGENT) return "🤖";
    return "🤖";
  };

  const getAgentName = (msg: Message) => {
    if (msg.author_type === AuthorType.USER) return "You";
    if (msg.author_type === AuthorType.AGENT) {
      // Use specific agent name if available
      if (msg.agent_name) return msg.agent_name;
      // Check message_metadata for agent_name (from database)
      if (msg.message_metadata?.agent_name) return msg.message_metadata.agent_name;
      return "Agent";
    }
    return "Agent";
  };

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme as any);
  };

  const triggerMention = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const newMessage =
      message.slice(0, cursorPos) + "@" + message.slice(cursorPos);

    setMessage(newMessage);
    setShowMentions(true);
    setMentionSearch("");
    setSelectedMentionIndex(0);

    setTimeout(() => {
      textarea.focus();
      const newCursorPos = cursorPos + 1;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  // Agent preview handlers
  const handleSubmitPreview = (preview_id: string, choice: string, edit_changes?: string) => {
    submitPreviewChoice(preview_id, choice, edit_changes);
  };

  // Notify parent about connection status (use isReady for accurate status)
  useEffect(() => {
    console.log("ChatPanelWS: isReady changed to", isReady, "- notifying parent");
    if (onConnectionChange) {
      onConnectionChange(isReady);
    }
  }, [isReady, onConnectionChange]);

  // Notify parent about sendMessage function
  useEffect(() => {
    if (onSendMessageReady) {
      onSendMessageReady(wsSendMessage);
    }
  }, [wsSendMessage, onSendMessageReady]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        mentionDropdownRef.current &&
        !mentionDropdownRef.current.contains(event.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(event.target as Node)
      ) {
        setShowMentions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (
      messagesContainerRef.current &&
      uniqueMessages.length > prevMessagesLengthRef.current
    ) {
      messagesContainerRef.current.scrollTop =
        messagesContainerRef.current.scrollHeight;
    }
    prevMessagesLengthRef.current = uniqueMessages.length;
  }, [uniqueMessages.length]);

  return (
    <div className="flex flex-col h-full bg-background">
      {sidebarCollapsed && (
        <div className="flex items-center gap-2 px-3 py-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            onMouseEnter={() => onSidebarHover(true)}
            className="w-8 h-8 text-foreground hover:bg-accent"
          >
            <PanelRightClose className="w-5 h-5" />
          </Button>
          <div className="flex-1" />
          {!isReady && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" />
              Connecting...
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="w-8 h-8 text-foreground hover:bg-accent"
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? (
              <Moon className="w-4 h-4" />
            ) : (
              <Sun className="w-4 h-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onCollapse}
            className="w-8 h-8 text-foreground hover:bg-accent"
            title="Hide chat panel"
          >
            <ChevronsLeft className="w-4 h-4" />
          </Button>
        </div>
      )}

      {!sidebarCollapsed && (
        <div className="flex items-center justify-between gap-2 px-3 py-2">
          <div className="flex items-center gap-2">
            {!isReady && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                Connecting...
              </div>
            )}
            {isReady && (
              <div className="flex items-center gap-2 text-xs text-green-600">
                <div className="w-2 h-2 bg-green-600 rounded-full" />
                Connected
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="w-8 h-8 text-foreground hover:bg-accent"
              title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4" />
              ) : (
                <Sun className="w-4 h-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onCollapse}
              className="w-8 h-8 text-foreground hover:bg-accent"
              title="Hide chat panel"
            >
              <PanelLeftClose className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
      >
        {uniqueMessages.map((msg) => {
          const isUserMessage = msg.author_type === AuthorType.USER;
          const isExpanded = expandedMessages.has(msg.id);
          const shouldTruncate = msg.content.length > 200;

          if (isUserMessage) {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[70%]">
                  <div className="space-y-1.5">
                    <div className="rounded-lg px-3 py-2 bg-muted w-fit ml-auto">
                      <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                        {msg.content}
                      </div>
                    </div>
                    <div className="flex items-center justify-end gap-2 px-1">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(msg.created_at)}
                      </span>
                      <button
                        onClick={() => copyToClipboard(msg.content, msg.id)}
                        className="p-1 rounded hover:bg-accent transition-colors"
                        title="Copy message"
                      >
                        {copiedMessageId === msg.id ? (
                          <Check className="w-3.5 h-3.5 text-green-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          }

          // Agent/System message
          // Check if this is a structured message (preview)
          if (msg.message_type && msg.message_type !== 'text' && msg.structured_data) {
            return (
              <div key={msg.id} className="flex gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
                  {getAgentAvatar(msg.author_type)}
                </div>
                <div className="flex-1 space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">
                    {getAgentName(msg)}
                  </div>
                  {/* Show text content if available */}
                  {msg.content && (
                    <div className="space-y-1.5">
                      <div className="rounded-lg px-3 py-2 bg-muted w-fit">
                        <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                          {msg.content}
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Show preview card */}
                  <MessagePreviewCard message={msg} />
                </div>
              </div>
            );
          }

          return (
            <div key={msg.id} className="flex gap-3">
              <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
                {getAgentAvatar(msg.author_type)}
              </div>

              <div className="flex-1 space-y-2">
                <div className="text-xs font-medium text-muted-foreground">
                  {getAgentName(msg)}
                </div>

                <div className="space-y-1.5">
                  <div className="rounded-lg px-3 py-2 bg-muted w-fit">
                    <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                      {shouldTruncate && !isExpanded
                        ? msg.content.slice(0, 200) + "..."
                        : msg.content}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(msg.created_at)}
                    </span>
                    <button
                      onClick={() => copyToClipboard(msg.content, msg.id)}
                      className="p-1 rounded hover:bg-accent transition-colors"
                      title="Copy message"
                    >
                      {copiedMessageId === msg.id ? (
                        <Check className="w-3.5 h-3.5 text-green-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                      )}
                    </button>
                    {shouldTruncate && (
                      <button
                        onClick={() => toggleExpand(msg.id)}
                        className="p-1 hover:bg-accent rounded transition-colors"
                        title={isExpanded ? "Collapse" : "Expand"}
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-3.5 h-3.5 text-foreground" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5 text-foreground" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Waiting for agent response indicator */}
        {isWaitingForResponse && typingAgents.length === 0 && !agentProgress.isExecuting && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
              🤖
            </div>
            <div className="flex-1 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">
                Agent
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-sm">Đang xử lý...</span>
              </div>
            </div>
          </div>
        )}

        {typingAgents.length > 0 && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
              🔧
            </div>
            <div className="flex-1 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">
                {typingAgents[0]}
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-sm">typing...</span>
              </div>
            </div>
          </div>
        )}

        {/* Agent Status Indicator - shows thinking/acting/waiting status */}
        {agentStatus.status !== 'idle' && (
          <div className="flex gap-3 p-4 bg-muted/50 rounded-lg border">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
              🤖
            </div>
            <div className="flex-1">
              <AgentStatusIndicator
                status={agentStatus.status}
                agentName={agentStatus.agentName || undefined}
                currentAction={agentStatus.currentAction}
              />
            </div>
          </div>
        )}
      </div>

      <div className="p-2 m-4 rounded-4xl relative bg-muted">
        {showMentions && filteredAgents.length > 0 && (
          <div
            ref={mentionDropdownRef}
            className="absolute bottom-full left-0 right-0 mb-2 mx-1 bg-card border border-border rounded-lg shadow-lg overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2 border-b border-border">
              <span className="text-sm font-medium text-foreground">
                Group Members
              </span>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 text-xs bg-accent rounded">
                  Tab
                </kbd>
                to select
              </span>
            </div>
            <div className="max-h-[240px] overflow-y-auto">
              {filteredAgents.map((agent, index) => (
                <button
                  key={agent.name}
                  onClick={() => insertMention(agent.name)}
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-accent/50 transition-colors ${index === selectedMentionIndex ? "bg-accent/50" : ""
                    }`}
                >
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 bg-muted">
                    {agent.avatar}
                  </div>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium text-foreground">
                      {agent.name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {agent.role}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="bg-transparent rounded-4xl p-1 border-0">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            className="min-h-[40px] resize-none bg-transparent border-0 text-sm text-foreground placeholder:text-muted-foreground p-1 focus-visible:ring-0 focus-visible:ring-transparent focus-visible:ring-offset-0"
            disabled={!isReady}
          />
          <div className="flex items-center justify-between pt-3">
            <div className="flex gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-accent"
                      onClick={triggerMention}
                      disabled={!isReady}
                    >
                      <AtSign className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Mention an agent</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <TechStackDialog />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>View tech stack</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Button
              size="icon"
              className="h-8 w-8 rounded-lg bg-primary hover:bg-primary/90"
              onClick={handleSend}
              disabled={!isReady || !message.trim()}
            >
              <ArrowUp className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Agent Preview Modal */}
      <AgentPreviewModal
        preview={pendingPreviews[0] || null}
        onSubmit={handleSubmitPreview}
        onClose={closePreview}
      />
    </div>
  );
}
