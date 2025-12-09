import type React from "react";
import { useState, useRef, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
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
  Crown,
  PaperclipIcon,
  FileText,
} from "lucide-react";
import { TechStackDialog } from "./tech-stack-dialog";
import { useTheme } from "@/components/provider/theme-provider";
import { useChatWebSocket } from "@/hooks/useChatWebSocket";
import { TypingIndicator } from "./TypingIndicator";
import { useAuth } from "@/hooks/useAuth";
import { useInfiniteMessages, useCreateMessageWithFile } from "@/queries/messages";
import { messagesApi } from "@/apis/messages";
import { AuthorType, type Message } from "@/types/message";
import { MessageStatusIndicator } from "./message-status-indicator";
import { AgentQuestionCard } from "./AgentQuestionCard";
import { BatchQuestionsCard } from "./BatchQuestionsCard";
import { ConversationOwnerBadge } from "./ConversationOwnerBadge";
import { AgentHandoffNotification } from "./AgentHandoffNotification";
import { ArtifactCard } from "./ArtifactCard";
import { StoriesCreatedCard } from "./StoriesCreatedCard";
import { StorySuggestionsCard } from "./StorySuggestionsCard";
import { PrdCreatedCard } from "./PrdCreatedCard";
import { StoriesFileCard } from "./StoriesFileCard";
import { useProjectAgents } from "@/queries/agents";
import { PromptInput, PromptInputButton, PromptInputSubmit, PromptInputTextarea, PromptInputToolbar, PromptInputTools } from "../ui/shadcn-io/ai/prompt-input";
import { MentionDropdown, type Agent } from "../ui/mention-dropdown";

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
  onAgentStatusesChange?: (statuses: Map<string, { status: string; lastUpdate: string }>) => void; // NEW
  onOpenArtifact?: (artifactId: string) => void;
  onOpenFile?: (filePath: string) => void;
  onInsertMentionReady?: (fn: (agentName: string) => void) => void; // Callback to insert @mention
}

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
  onAgentStatusesChange, // NEW
  onOpenArtifact,
  onOpenFile,
  onInsertMentionReady,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState("");
  const [mentionedAgent, setMentionedAgent] = useState<{ id: string; name: string } | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<Message | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const prevMessagesLengthRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Get access token
  const token = localStorage.getItem("access_token");

  // File upload mutation
  const { mutateAsync: createMessageWithFile, isPending: isUploading } = useCreateMessageWithFile();

  // Fetch real agents from database
  const { data: projectAgents, isLoading: agentsLoading } = useProjectAgents(projectId || "", {
    enabled: !!projectId,
  });

  // Map role_type to user-friendly designation, icon and color
  const getRoleInfo = (roleType: string): { role: string; icon: string; color: string } => {
    const roleMap: Record<string, { role: string; icon: string; color: string }> = {
      team_leader: { role: "Team Leader", icon: "👨‍💼", color: "#6366f1" },
      business_analyst: { role: "Business Analyst", icon: "👩‍💼", color: "#8b5cf6" },
      developer: { role: "Developer", icon: "👨‍💻", color: "#10b981" },
      tester: { role: "Tester", icon: "🧪", color: "#f59e0b" },
    };
    return roleMap[roleType] || { role: roleType, icon: "🤖", color: "#6b7280" };
  };

  // Transform database agents to dropdown format
  // Handle both { data: [...] } and direct array response
  const agentsList = Array.isArray(projectAgents) 
    ? projectAgents 
    : (projectAgents?.data || []);
  
  const AGENTS = agentsList.map((agent) => {
    const roleInfo = getRoleInfo(agent.role_type);
    return {
      id: agent.id,
      name: agent.human_name,
      role: roleInfo.role,
      icon: roleInfo.icon,
      color: roleInfo.color,
    };
  });

  // Fetch existing messages with infinite scroll
  const {
    data: messagesData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isLoadingMessages,
  } = useInfiniteMessages(projectId || "");

  // Flatten all pages into single array of messages
  // API returns messages in DESC order (newest first)
  // We need to reverse to get chronological order (oldest first for display)
  const apiMessages = messagesData?.pages
    ? messagesData.pages.flatMap(page => page.messages).reverse()
    : [];
  const totalMessageCount = messagesData?.pages?.[0]?.totalCount || 0;

  // Ref for scroll position preservation when loading older messages
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  const isLoadingMoreRef = useRef(false);

  // Debug log for API messages
  useEffect(() => {
    if (messagesData && messagesData.pages?.length > 0) {
      console.log('[ChatPanel] 📊 Messages loaded:', {
        total: totalMessageCount,
        loaded: apiMessages.length,
        pages: messagesData.pages?.length,
        hasOlder: hasNextPage,
      })
    }
  }, [messagesData, totalMessageCount, apiMessages.length, hasNextPage])

  // Intersection Observer for infinite scroll - load more when scrolling to top
  useEffect(() => {
    const trigger = loadMoreTriggerRef.current;
    const container = messagesContainerRef.current;
    if (!trigger || !container) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage && !isLoadingMoreRef.current) {
          console.log('[ChatPanel] 🔄 Loading more messages...');
          isLoadingMoreRef.current = true;
          
          // Save scroll position before loading
          const scrollHeightBefore = container.scrollHeight;
          const scrollTopBefore = container.scrollTop;
          
          fetchNextPage().then(() => {
            // Restore scroll position after loading (to prevent jump)
            requestAnimationFrame(() => {
              const scrollHeightAfter = container.scrollHeight;
              const heightDiff = scrollHeightAfter - scrollHeightBefore;
              container.scrollTop = scrollTopBefore + heightDiff;
              isLoadingMoreRef.current = false;
              console.log('[ChatPanel] ✅ Scroll position restored');
            });
          });
        }
      },
      { 
        root: container,
        threshold: 0.1,
        rootMargin: '100px 0px 0px 0px' // Trigger 100px before reaching top
      }
    );

    observer.observe(trigger);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // WebSocket connection (simplified with 5 message types)
  const {
    isConnected,
    messages: wsMessages,
    agentStatus,
    agentStatuses: wsAgentStatuses,  // Individual agent statuses from WebSocket
    typingAgents,
    answeredBatchIds,  // Track which batches have been answered
    conversationOwner,
    sendMessage: wsSendMessage,
    sendQuestionAnswer,
    sendBatchAnswers,
  } = useChatWebSocket(projectId ?? null, token || '');

  // Notify parent when agent statuses change
  useEffect(() => {
    if (onAgentStatusesChange && wsAgentStatuses.size > 0) {
      console.log('[ChatPanel] Agent statuses changed:', Object.fromEntries(wsAgentStatuses));
      onAgentStatusesChange(wsAgentStatuses);
    }
  }, [wsAgentStatuses, onAgentStatusesChange]);

  // Combine existing messages with WebSocket messages
  const wsMessagesArray = wsMessages || [];

  // Combine API messages with WebSocket messages (no temp messages anymore)
  const allMessages = [...apiMessages, ...wsMessagesArray]

  // Sort by created_at timestamp
  const sortedMessages = allMessages.sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )

  // Remove duplicates by ID (simple de-duplication)
  const deduplicatedMessages = sortedMessages.filter(
    (msg, index, self) => index === self.findIndex(m => m.id === msg.id)
  );

  // Group batch questions: handle both new format (1 message with all questions) and old format (multiple messages)
  const uniqueMessages = (() => {
    const processedBatchIds = new Set<string>();
    const result: Message[] = [];

    for (const msg of deduplicatedMessages) {
      // If this is a batch question
      if (msg.message_type === 'agent_question_batch' && msg.structured_data?.batch_id) {
        const batchId = msg.structured_data.batch_id;
        
        // Skip if we already processed this batch
        if (processedBatchIds.has(batchId)) {
          continue;
        }
        processedBatchIds.add(batchId);

        // NEW FORMAT: structured_data.questions already contains all questions
        if (msg.structured_data?.questions && Array.isArray(msg.structured_data.questions) && msg.structured_data.questions.length > 0) {
          // Use as-is, questions are already in correct format
          result.push(msg);
          continue;
        }

        // OLD FORMAT: Multiple messages per batch - need to combine them
        const batchMessages = deduplicatedMessages.filter(
          m => m.message_type === 'agent_question_batch' && 
               m.structured_data?.batch_id === batchId
        ).sort((a, b) => (a.structured_data?.batch_index || 0) - (b.structured_data?.batch_index || 0));

        // Combine into single message with all questions (from old format where content = question text)
        const combinedQuestions = batchMessages.map(m => ({
          question_id: m.structured_data?.question_id,
          question_text: m.content,  // Old format: content was the question text
          question_type: m.structured_data?.question_type || 'open',
          options: m.structured_data?.options,
          allow_multiple: m.structured_data?.allow_multiple || false,
        }));

        const combinedQuestionIds = batchMessages.map(m => m.structured_data?.question_id || m.id);
        const isAnswered = batchMessages.some(m => m.structured_data?.answered);

        const combinedMsg: Message = {
          ...batchMessages[0],
          structured_data: {
            ...batchMessages[0].structured_data,
            batch_id: batchId,
            questions: combinedQuestions,
            question_ids: combinedQuestionIds,
            answered: isAnswered,
          }
        };

        result.push(combinedMsg);
      } else {
        // Non-batch message, add as-is
        result.push(msg);
      }
    }

    return result;
  })();
  
  // Find the latest PRD card ID (only show actions on the latest one)
  const latestPrdMessageId = (() => {
    const prdMessages = uniqueMessages.filter(
      msg => msg.structured_data?.message_type === 'prd_created'
    )
    if (prdMessages.length === 0) return null
    // Get the one with latest timestamp
    const latest = prdMessages.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0]
    return latest?.id || null
  })()
  
  // Find the latest Stories card ID (only show actions on the latest one)
  const latestStoriesMessageId = (() => {
    const storiesMessages = uniqueMessages.filter(
      msg => msg.structured_data?.message_type === 'stories_created'
    )
    if (storiesMessages.length === 0) return null
    const latest = storiesMessages.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0]
    return latest?.id || null
  })()

  // Check if a PRD/Stories card has been submitted (user sent approve/edit message after it)
  const isCardSubmitted = (cardMsgId: string, cardType: 'prd' | 'stories'): boolean => {
    const cardMsgIndex = uniqueMessages.findIndex(m => m.id === cardMsgId)
    if (cardMsgIndex === -1) return false
    
    // Look for user messages after this card
    const messagesAfterCard = uniqueMessages.slice(cardMsgIndex + 1)
    const keywords = cardType === 'prd' 
      ? ['Approve PRD', 'Edit PRD']
      : ['Approve Stories', 'Edit Stories']
    
    return messagesAfterCard.some(m => 
      m.author_type === AuthorType.USER && 
      keywords.some(kw => m.content?.includes(kw))
    )
  }

  // Detect unanswered questions - show only the LATEST one
  useEffect(() => {
    // Find ALL unanswered questions
    const unansweredQuestions = uniqueMessages.filter(
      msg => msg.message_type === 'agent_question' && !msg.structured_data?.answered
    )

    // Get LATEST by timestamp (most recent)
    const latestUnanswered = unansweredQuestions.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0]

    setPendingQuestion(latestUnanswered || null)

    // Auto-scroll to question if it appears (only if it's a NEW question)
    if (latestUnanswered && latestUnanswered.id !== pendingQuestion?.id) {
      setTimeout(() => {
        const element = document.getElementById(`question-${latestUnanswered.id}`)
        element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 100)
    }
  }, [uniqueMessages])

  // Detect stories_approved message and refresh Kanban board
  const lastApprovedMsgIdRef = useRef<string | null>(null)
  useEffect(() => {
    // Find the MOST RECENT stories_approved message (not the first one)
    const approvedMessages = uniqueMessages.filter(
      msg => msg.structured_data?.message_type === 'stories_approved'
    )
    const latestApproved = approvedMessages.length > 0
      ? approvedMessages.sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )[0]
      : null
    
    // Only refresh if it's a NEW approval message we haven't processed yet
    if (latestApproved && latestApproved.id !== lastApprovedMsgIdRef.current && projectId) {
      console.log('[ChatPanel] Stories approved, refreshing Kanban board...', latestApproved.id)
      lastApprovedMsgIdRef.current = latestApproved.id
      // Use refetchQueries for immediate refetch instead of invalidateQueries
      queryClient.refetchQueries({ queryKey: ['kanban-board', projectId], type: 'active' })
    }
  }, [uniqueMessages, projectId, queryClient])

  // Detect project_reset message and refresh Kanban board (after deleting project data)
  const lastResetMsgIdRef = useRef<string | null>(null)
  useEffect(() => {
    const resetMessages = uniqueMessages.filter(
      msg => msg.structured_data?.message_type === 'project_reset'
    )
    const latestReset = resetMessages.length > 0
      ? resetMessages.sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )[0]
      : null
    
    if (latestReset && latestReset.id !== lastResetMsgIdRef.current && projectId) {
      console.log('[ChatPanel] Project reset, refreshing Kanban board...', latestReset.id)
      lastResetMsgIdRef.current = latestReset.id
      // Refresh Kanban board to clear deleted stories
      queryClient.refetchQueries({ queryKey: ['kanban-board', projectId], type: 'active' })
    }
  }, [uniqueMessages, projectId, queryClient])

  // Track if user manually scrolled up
  const userScrolledUpRef = useRef(false)
  // Force scroll to bottom (bypasses userScrolledUp check)
  const forceScrollRef = useRef(false)
  
  // Detect manual scroll
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const handleScroll = () => {
      // Don't update userScrolledUp if we're force scrolling
      if (forceScrollRef.current) return
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
      userScrolledUpRef.current = !isNearBottom
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  // Helper to scroll to bottom
  const scrollToBottom = (behavior: 'auto' | 'smooth' = 'smooth') => {
    const container = messagesContainerRef.current
    if (!container) return
    
    requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior
      })
      // Reset force scroll after scrolling
      setTimeout(() => {
        forceScrollRef.current = false
        userScrolledUpRef.current = false
      }, 100)
    })
  }

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const isFirstLoad = prevMessagesLengthRef.current === 0 && uniqueMessages.length > 0
    const hasNewMessages = uniqueMessages.length > prevMessagesLengthRef.current
    const shouldScroll = forceScrollRef.current || !userScrolledUpRef.current

    if (isFirstLoad || (hasNewMessages && shouldScroll)) {
      scrollToBottom(isFirstLoad ? 'auto' : 'smooth')
    }

    prevMessagesLengthRef.current = uniqueMessages.length
  }, [uniqueMessages])

  // Auto-scroll when typing indicator appears
  const typingAgentsCount = typingAgents.size
  const prevTypingCountRef = useRef(0)
  
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    // Only scroll when typing starts (count goes from 0 to >0), not on every update
    const typingJustStarted = prevTypingCountRef.current === 0 && typingAgentsCount > 0
    prevTypingCountRef.current = typingAgentsCount
    const shouldScroll = forceScrollRef.current || !userScrolledUpRef.current

    if (typingJustStarted && shouldScroll) {
      scrollToBottom()
    }
  }, [typingAgentsCount])

  // Determine if chat should be blocked
  const isMultichoiceQuestion = pendingQuestion?.structured_data?.question_type === 'multichoice'
  const isAgentTyping = typingAgents.size > 0
  const shouldBlockChat = (pendingQuestion && isMultichoiceQuestion) || isAgentTyping

  // Note: Kanban, activeTab, and agentStatuses features removed for simplicity

  const filteredAgents = AGENTS.filter((agent) =>
    agent.name.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  const insertMention = (agent: Agent) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = message.slice(0, cursorPos);
    const textAfterCursor = message.slice(cursorPos);

    const atIndex = textBeforeCursor.lastIndexOf("@");
    const newText =
      textBeforeCursor.slice(0, atIndex) + `@${agent.name} ` + textAfterCursor;

    setMessage(newText);
    setShowMentions(false);
    setMentionSearch("");

    // Store the mentioned agent for routing
    setMentionedAgent({ id: agent.id, name: agent.name });

    setTimeout(() => {
      const newCursorPos = atIndex + agent.name.length + 2;
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
    } else {
      setShowMentions(false);
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault(); // Prevent form submission from navigating
    if (!message.trim() && !selectedFile) return;
    if (!isConnected && !selectedFile) {
      console.error("WebSocket not connected");
      return;
    }

    let finalMessage = message.trim();

    // Check if this is answering an open question
    if (pendingQuestion && pendingQuestion.structured_data?.question_type === 'open') {
      // Send as question answer instead of regular message
      sendQuestionAnswer(
        pendingQuestion.structured_data.question_id!,
        finalMessage,
        undefined
      )
      setMessage("");
      setPendingQuestion(null); // Hide notification immediately
      // Force scroll to bottom after sending
      forceScrollRef.current = true;
      return;
    }

    // Handle file upload via REST API
    if (selectedFile && projectId) {
      try {
        await createMessageWithFile({
          project_id: projectId,
          content: finalMessage || "Analyze this document",
          file: selectedFile,
        });
        setSelectedFile(null);
        setMessage("");
        // Force scroll to bottom after sending
        forceScrollRef.current = true;
      } catch (error) {
        console.error("Failed to upload file:", error);
        alert("Failed to upload file. Please try again.");
      }
      return;
    }

    // Send via WebSocket with agent routing info if agent was mentioned
    wsSendMessage(finalMessage, mentionedAgent?.name);

    setMessage("");
    setMentionedAgent(null);  // Clear mentioned agent after sending
    
    // Force scroll to bottom after sending
    forceScrollRef.current = true;
    
    // Focus textarea
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  };

  // Reset waiting state when we receive agent messages or agent starts typing/processing
  useEffect(() => {
    if (wsMessagesArray && wsMessagesArray.length > 0) {
      const lastMessage = wsMessagesArray[wsMessagesArray.length - 1];
      if (lastMessage.author_type === AuthorType.AGENT) {
        setIsWaitingForResponse(false);
      }
    }
  }, [wsMessagesArray]);

  // Reset waiting state when agent status changes
  useEffect(() => {
    if (agentStatus !== 'idle') {
      setIsWaitingForResponse(false);
    }
  }, [agentStatus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // MentionDropdown handles its own keyboard navigation (Arrow, Tab, Enter, Escape)
    // Only handle Enter to send when dropdown is NOT shown
    if (!showMentions && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // Always prevent default (new line)
      if (!shouldBlockChat) {
        handleSend(); // Only send if chat is not blocked
      }
    }
  };

  const copyToClipboard = async (content: string | undefined, messageId: string) => {
    try {
      if (!content) {
        console.warn("No content to copy");
        return;
      }
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      // Automatically converts UTC to local time and formats
      return format(date, 'h:mm a \'on\' MMM dd');
      // Output example: "10:30 AM on Nov 25"
    } catch (error) {
      console.error('Error formatting timestamp:', error);
      return dateStr;
    }
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

    setTimeout(() => {
      textarea.focus();
      const newCursorPos = cursorPos + 1;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  // Notify parent about connection status
  useEffect(() => {
    console.log("ChatPanelWS: connection changed to", isConnected);
    if (onConnectionChange) {
      onConnectionChange(isConnected);
    }
  }, [isConnected, onConnectionChange]);

  // Expose insertMention function to parent for @mention from agent popup
  useEffect(() => {
    if (onInsertMentionReady) {
      const insertMentionByName = (agentName: string) => {
        const agent = AGENTS.find(a => a.name === agentName);
        if (agent) {
          // Insert @agentName at the start of the message
          setMessage(`@${agentName} `);
          setMentionedAgent({ id: agent.id, name: agent.name });
          // Focus the textarea
          setTimeout(() => {
            textareaRef.current?.focus();
          }, 100);
        }
      };
      onInsertMentionReady(insertMentionByName);
    }
  }, [onInsertMentionReady, AGENTS]);



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

          {/* Conversation Owner Display (collapsed sidebar) */}
          {conversationOwner && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20">
              <Crown className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
              <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">
                {conversationOwner.agentName} is receiving questions
              </span>
            </div>
          )}

          <div className="flex-1" />
          {!isConnected && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" />
              Connecting...
            </div>
          )}
          {/* <Button
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
          </Button> */}
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
            {!isConnected && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                Connecting...
              </div>
            )}
            {isConnected && (
              <div className="flex items-center gap-2 text-xs text-green-600">
                <div className="w-2 h-2 bg-green-600 rounded-full" />
                Connected
              </div>
            )}

            {/* Conversation Owner Display */}
            {conversationOwner && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20">
                <Crown className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
                <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">
                  {conversationOwner.agentName} is receiving questions
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
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
        {/* Infinite scroll trigger - loads more messages when visible */}
        <div ref={loadMoreTriggerRef} className="h-1" />
        
        {/* Loading indicator for older messages */}
        {isFetchingNextPage && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading older messages...</span>
          </div>
        )}
        
        {/* Show how many messages loaded / total */}
        {hasNextPage && !isFetchingNextPage && totalMessageCount > 0 && (
          <div className="flex items-center justify-center py-2">
            <button 
              onClick={() => fetchNextPage()}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              ↑ Load older messages ({apiMessages.length} / {totalMessageCount})
            </button>
          </div>
        )}

        {uniqueMessages.map((msg) => {
          const isUserMessage = msg.author_type === AuthorType.USER;

          if (isUserMessage) {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[70%]">
                  <div className="space-y-1.5">
                    {/* File attachment display */}
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex flex-col gap-1.5 items-end">
                        {msg.attachments.map((att, idx) => (
                          <button
                            key={idx}
                            onClick={() => messagesApi.downloadAttachment(msg.id, att.filename, idx)}
                            className="flex items-center gap-3 px-3 py-2.5 bg-muted border border-border rounded-lg w-fit hover:bg-accent transition-colors cursor-pointer"
                            title={`Download ${att.filename}`}
                          >
                            <div className="flex items-center justify-center w-10 h-10 bg-primary/15 rounded-lg">
                              <FileText className="w-5 h-5 text-primary" />
                            </div>
                            <div className="flex flex-col items-start">
                              <span className="text-sm font-medium text-foreground">
                                {att.filename}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {(att.file_size / 1024).toFixed(1)} KB
                              </span>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                    {/* Message content */}
                    <div className="rounded-lg px-3 py-2 bg-muted w-fit ml-auto">
                      <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                        {msg.content || ''}
                      </div>
                    </div>
                    <div className="flex items-center justify-end gap-2 px-1">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(msg.created_at)}
                      </span>
                      {/* Message status indicator for user messages */}
                      {msg.status && <MessageStatusIndicator status={msg.status} />}
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

          // Activity messages are now shown in the execution dialog
          // Skip rendering them here
          if (msg.message_type === 'activity') {
            return null;
          }

          // Skip project_reset messages (internal notification for Kanban refresh, not for display)
          if (msg.structured_data?.message_type === 'project_reset') {
            return null;
          }

          // Agent Handoff Notification
          if (msg.message_type === 'agent_handoff') {
            return (
              <AgentHandoffNotification
                key={msg.id}
                previousAgent={msg.structured_data?.previous_agent_name}
                newAgent={msg.structured_data?.new_agent_name || ''}
                reason={msg.structured_data?.reason || ''}
                timestamp={msg.created_at}
              />
            );
          }

          // Agent Question Handling
          if (msg.message_type === 'agent_question') {
            return (
              <div key={msg.id} id={`question-${msg.id}`} className="flex gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
                  ❓
                </div>
                <div className="flex-1">
                  <div className="text-xs font-medium text-muted-foreground mb-2">
                    {msg.agent_name || 'Agent'}
                  </div>
                  <AgentQuestionCard
                    question={msg.content}
                    questionType={msg.structured_data?.question_type || 'open'}
                    options={msg.structured_data?.options || []}
                    allowMultiple={msg.structured_data?.allow_multiple || false}
                    answered={msg.structured_data?.answered || false}
                    processing={msg.structured_data?.processing || false}
                    userAnswer={msg.structured_data?.user_answer}
                    userSelectedOptions={msg.structured_data?.user_selected_options}
                    agentName={msg.agent_name}
                    onSubmit={(answer, selectedOptions) => {
                      sendQuestionAnswer(
                        msg.structured_data!.question_id!,
                        answer,
                        selectedOptions
                      )
                      setPendingQuestion(null) // Hide notification immediately
                    }}
                  />
                </div>
              </div>
            );
          }

          // Batch Question Handling
          if (msg.message_type === 'agent_question_batch') {
            return (
              <div key={msg.id} id={`batch-${msg.id}`} className="flex gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
                  ❓
                </div>
                <div className="flex-1">
                  <div className="text-xs font-medium text-muted-foreground mb-2">
                    {msg.agent_name || 'Agent'}
                  </div>
                  <BatchQuestionsCard
                    batchId={msg.structured_data?.batch_id || ''}
                    questions={msg.structured_data?.questions || []}
                    questionIds={msg.structured_data?.question_ids || []}
                    agentName={msg.agent_name}
                    answered={msg.structured_data?.answered || answeredBatchIds.has(msg.structured_data?.batch_id || '')}
                    submittedAnswers={msg.structured_data?.answers || []}
                    onSubmit={(answers) => {
                      sendBatchAnswers(
                        msg.structured_data!.batch_id!,
                        answers
                      )
                    }}
                  />
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
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {getAgentName(msg)}
                  </span>

                  {/* Conversation Owner Badge */}
                  {msg.author_type === AuthorType.AGENT && conversationOwner && conversationOwner.agentName === msg.agent_name && conversationOwner.status && (
                    <ConversationOwnerBadge
                      agentName={msg.agent_name || ''}
                      isOwner={true}
                      status={conversationOwner.status}
                    />
                  )}
                </div>

                <div className="space-y-1.5">
                  {/* Only show content bubble if there's actual content */}
                  {msg.content && msg.content.trim() && (
                    <>
                      <div className="rounded-lg px-3 py-2 bg-muted w-fit">
                        <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                          {msg.content}
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
                      </div>
                    </>
                  )}
                  
                  {/* Show artifact card if message type is artifact_created */}
                  {msg.message_type === 'artifact_created' && msg.structured_data?.artifact_id && (
                    <ArtifactCard
                      artifact={{
                        artifact_id: msg.structured_data.artifact_id,
                        artifact_type: msg.structured_data.artifact_type || 'analysis',
                        title: msg.structured_data.title || 'Artifact',
                        description: msg.structured_data.description,
                        version: msg.structured_data.version || 1,
                        status: msg.structured_data.status || 'draft',
                        agent_name: msg.structured_data.agent_name || msg.agent_name || getAgentName(msg),
                      }}
                      onClick={() => {
                        if (onOpenArtifact && msg.structured_data?.artifact_id) {
                          onOpenArtifact(msg.structured_data.artifact_id)
                        }
                      }}
                    />
                  )}
                  
                  {/* Show PRD created card if structured_data has message_type prd_created */}
                  {msg.structured_data?.message_type === 'prd_created' && msg.structured_data?.file_path && (
                    <PrdCreatedCard
                      title={msg.structured_data.title || 'PRD'}
                      filePath={msg.structured_data.file_path}
                      status={msg.structured_data.status || 'pending'}
                      showActions={msg.id === latestPrdMessageId}
                      submitted={msg.structured_data.submitted === true || isCardSubmitted(msg.id, 'prd')}
                      onView={() => {
                        if (onOpenFile) {
                          onOpenFile(msg.structured_data!.file_path)
                        }
                        if (onActiveTabChange) {
                          onActiveTabChange('file')
                        }
                      }}
                      onApprove={() => {
                        wsSendMessage("Approve this PRD, please create user stories")
                      }}
                      onEdit={(feedback) => {
                        wsSendMessage(`Edit PRD: ${feedback}`)
                      }}
                    />
                  )}
                  
                  {/* Show stories file card if structured_data has message_type stories_created */}
                  {msg.structured_data?.message_type === 'stories_created' && msg.structured_data?.file_path && (
                    <StoriesFileCard
                      filePath={msg.structured_data.file_path}
                      status={msg.structured_data.status || 'pending'}
                      showActions={msg.id === latestStoriesMessageId}
                      submitted={msg.structured_data.submitted === true || isCardSubmitted(msg.id, 'stories')}
                      onView={() => {
                        if (onOpenFile) {
                          onOpenFile(msg.structured_data!.file_path)
                        }
                        if (onActiveTabChange) {
                          onActiveTabChange('file')
                        }
                      }}
                      onApprove={() => {
                        wsSendMessage("Approve Stories")
                      }}
                      onEdit={(feedback) => {
                        wsSendMessage(`Edit Stories: ${feedback}`)
                      }}
                    />
                  )}
                  
                  {/* Show stories created card if message type is stories_created (legacy) */}
                  {msg.message_type === 'stories_created' && msg.structured_data?.story_ids && (
                    <StoriesCreatedCard
                      stories={{
                        count: msg.structured_data.count || 0,
                        story_ids: msg.structured_data.story_ids || [],
                        prd_artifact_id: msg.structured_data.prd_artifact_id,
                      }}
                      projectId={projectId || ''}
                    />
                  )}
                  
                  {/* Show story review card from BA auto-verify */}
                  {msg.structured_data?.message_type === 'story_review' && (
                    <StorySuggestionsCard
                      storyId={msg.structured_data.story_id || ''}
                      storyTitle={msg.structured_data.story_title || ''}
                      isDuplicate={msg.structured_data.is_duplicate}
                      duplicateOf={msg.structured_data.duplicate_of}
                      investScore={msg.structured_data.invest_score || 0}
                      investIssues={msg.structured_data.invest_issues || []}
                      suggestedTitle={msg.structured_data.suggested_title}
                      suggestedAcceptanceCriteria={msg.structured_data.suggested_acceptance_criteria}
                      suggestedRequirements={msg.structured_data.suggested_requirements}
                      hasSuggestions={msg.structured_data.has_suggestions}
                      initialActionTaken={msg.structured_data.action_taken}
                      onApplied={async (updatedStory) => {
                        if (projectId) {
                          console.log('[ChatPanel] onApplied called with updated story:', updatedStory)
                          // Update cache directly with new story data for immediate UI update
                          if (updatedStory) {
                            queryClient.setQueryData(['kanban-board', projectId], (oldData: any) => {
                              if (!oldData?.board) return oldData
                              // Update story in the appropriate column
                              const newBoard = { ...oldData.board }
                              for (const column of Object.keys(newBoard)) {
                                newBoard[column] = newBoard[column].map((story: any) => 
                                  story.id === updatedStory.id 
                                    ? { ...story, title: updatedStory.title, acceptance_criteria: updatedStory.acceptance_criteria, requirements: updatedStory.requirements }
                                    : story
                                )
                              }
                              console.log('[ChatPanel] Updated kanban cache with new story data')
                              return { ...oldData, board: newBoard }
                            })
                          }
                          // Also refetch to ensure consistency
                          await queryClient.refetchQueries({ 
                            queryKey: ['kanban-board', projectId],
                            type: 'all'
                          })
                          queryClient.invalidateQueries({ queryKey: ['messages', { project_id: projectId }] })
                        }
                      }}
                      onKeep={() => {
                        if (projectId) {
                          queryClient.invalidateQueries({ queryKey: ['messages', { project_id: projectId }] })
                        }
                      }}
                      onRemove={async (removedStoryId) => {
                        if (projectId) {
                          console.log('[ChatPanel] onRemove called for story:', removedStoryId)
                          // Remove story from cache directly for immediate UI update
                          if (removedStoryId) {
                            queryClient.setQueryData(['kanban-board', projectId], (oldData: any) => {
                              if (!oldData?.board) return oldData
                              const newBoard = { ...oldData.board }
                              for (const column of Object.keys(newBoard)) {
                                newBoard[column] = newBoard[column].filter((story: any) => story.id !== removedStoryId)
                              }
                              console.log('[ChatPanel] Removed story from kanban cache')
                              return { ...oldData, board: newBoard }
                            })
                          }
                          // Also refetch to ensure consistency
                          await queryClient.refetchQueries({ 
                            queryKey: ['kanban-board', projectId],
                            type: 'all'
                          })
                          queryClient.invalidateQueries({ queryKey: ['messages', { project_id: projectId }] })
                        }
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing Indicators*/}
        {Array.from(typingAgents.values()).map((typing) => (
          <TypingIndicator
            key={typing.id}
            agentName={typing.agent_name}
            message={typing.message}
          />
        ))}
      </div>

      {/* Chat Input Area - wrapped with question notification when pending */}
      <div className={`mx-4 mb-4 rounded-2xl relative ${pendingQuestion ? 'border border-blue-200 bg-blue-100 dark:bg-blue-900/50 dark:border-blue-800' : ''}`}>
        {/* Question Notification Banner */}
        {pendingQuestion && (
          <div className="px-4 py-3 bg-blue-100 dark:bg-blue-900/50 rounded-t-2xl">
            <div className="flex items-center justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm">❓</span>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {pendingQuestion.agent_name || 'Agent'} is waiting for your answer
                  </p>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-1">
                  {pendingQuestion.content}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const element = document.getElementById(`question-${pendingQuestion.id}`)
                  element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                }}
                className="text-xs text-blue-600 border-blue-300 hover:bg-blue-100 h-7 px-3"
              >
                View Question
              </Button>
            </div>
          </div>
        )}

        <div className={`p-2 ${pendingQuestion ? 'pt-3' : ''}`}>
        {showMentions && (
          <MentionDropdown
            agents={filteredAgents}
            onSelect={insertMention}
            onClose={() => setShowMentions(false)}
          />
        )}

        {/* Hidden file input */}
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept=".docx,.txt"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              // Validate size (10MB)
              if (file.size > 10 * 1024 * 1024) {
                alert("File too large. Limit: 10MB");
                e.target.value = "";
                return;
              }
              // Validate extension
              const fileName = file.name.toLowerCase();
              const allowedExtensions = ['.docx', '.txt'];
              const hasValidExt = allowedExtensions.some(ext => fileName.endsWith(ext));
              if (!hasValidExt) {
                alert("Only .docx and .txt files are supported");
                e.target.value = "";
                return;
              }
              setSelectedFile(file);
            }
            e.target.value = ""; // Reset to allow selecting same file again
          }}
        />

        {/* File preview */}
        {selectedFile && (
          <div className="flex items-center gap-2 px-3 py-2 mb-2 bg-muted rounded-lg">
            {isUploading ? (
              <Loader2 className="w-4 h-4 text-blue-500 flex-shrink-0 animate-spin" />
            ) : (
              <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
            )}
            <span className="text-sm truncate flex-1">
              {isUploading ? "Uploading..." : selectedFile.name}
            </span>
            {!isUploading && (
              <>
                <span className="text-xs text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setSelectedFile(null)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        )}

        {/* <div className="bg-transparent rounded-4xl p-1 border-0"> */}
        <PromptInput onSubmit={handleSend}
        >
          <PromptInputTextarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder={selectedFile ? "Add description for file..." : "Type your message..."}
          />
          <PromptInputToolbar>
            <PromptInputTools>
              <PromptInputButton
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className={selectedFile ? "text-blue-500" : ""}
              >
                <PaperclipIcon size={16} />
              </PromptInputButton>

            </PromptInputTools>
            <PromptInputSubmit disabled={(!isConnected && !selectedFile) || shouldBlockChat || isUploading || (!message.trim() && !selectedFile)} />
          </PromptInputToolbar>
        </PromptInput>
        {/* <div className="flex items-center justify-between pt-3">
          <div className="flex gap-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 hover:bg-accent"
                    onClick={triggerMention}
                    disabled={!isConnected || shouldBlockChat}
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
            disabled={!isConnected || !message.trim() || shouldBlockChat}
          >
            <ArrowUp className="w-4 h-4" />
          </Button>
        </div> */}

        </div>
      </div>

    </div>
  );
}
