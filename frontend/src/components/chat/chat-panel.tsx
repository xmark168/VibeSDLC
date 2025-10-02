
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Shuffle, User, Menu, ChevronDown, ChevronUp, ArrowUp } from "lucide-react"

interface ChatPanelProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
}

type MessageType = "thinking" | "question" | "reply"

interface Message {
  id: string
  agent: {
    name: string
    avatar: string
    colorClass: string
  }
  type: MessageType
  content: string
  expanded?: boolean
}

const AGENTS = [
  { name: "Mike", role: "Team Leader", avatar: "👨‍💼", colorClass: "agent-mike" },
  { name: "Emma", role: "Product Manager", avatar: "👩‍💼", colorClass: "agent-emma" },
  { name: "Bob", role: "Architect", avatar: "👨‍🔧", colorClass: "agent-bob" },
  { name: "Alex", role: "Engineer", avatar: "👨‍💻", colorClass: "agent-alex" },
  { name: "Developer", role: "Developer", avatar: "🔧", colorClass: "agent-developer" },
  { name: "Tester", role: "Tester", avatar: "🧪", colorClass: "agent-tester" },
]

export function ChatPanel({ sidebarCollapsed, onToggleSidebar }: ChatPanelProps) {
  const [message, setMessage] = useState("")
  const [showMentions, setShowMentions] = useState(false)
  const [mentionSearch, setMentionSearch] = useState("")
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const mentionDropdownRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      agent: {
        name: "Developer",
        avatar: "🔧",
        colorClass: "agent-developer",
      },
      type: "thinking",
      content:
        "Analyzing the codebase structure and identifying the best approach for implementing the multi-agent system...",
    },
    {
      id: "2",
      agent: {
        name: "Developer",
        avatar: "🔧",
        colorClass: "agent-developer",
      },
      type: "question",
      content:
        "Thanks — I have currency=VND, backend=localStorage, ship_from=Ho Chi Minh City, VAT=10% for Vietnam, domestic rates, domain/GA4/Pixel, brand, and social. To finalize, please provide the remaining details in this compact format:",
      expanded: true,
    },
    {
      id: "3",
      agent: {
        name: "User",
        avatar: "👤",
        colorClass: "",
      },
      type: "reply",
      content: "Race m",
    },
    {
      id: "4",
      agent: {
        name: "Tester",
        avatar: "🧪",
        colorClass: "agent-tester",
      },
      type: "thinking",
      content:
        "Set returns window to 14 days.\n\nExpand size_guide to include Women and Kids charts (placeholders unless you provide measurements).",
    },
    {
      id: "5",
      agent: {
        name: "Tester",
        avatar: "🧪",
        colorClass: "agent-tester",
      },
      type: "question",
      content:
        "Request for user input on various details for finalizing updates:\n\n• Done ✓ Tra Do Son's reply\n\nReply task: To finalize the updates, please provide these missing details:\n\n1. International shipping rates (for USA, Canada, UK, Australia)",
      expanded: false,
    },
  ])

  const activeAgent = {
    name: "Developer",
    avatar: "🔧",
    colorClass: "agent-developer",
  }

  const toggleExpand = (id: string) => {
    setMessages(messages.map((msg) => (msg.id === id ? { ...msg, expanded: !msg.expanded } : msg)))
  }

  const filteredAgents = AGENTS.filter((agent) => agent.name.toLowerCase().includes(mentionSearch.toLowerCase()))

  const insertMention = (agentName: string) => {
    const textarea = textareaRef.current
    if (!textarea) return

    const cursorPos = textarea.selectionStart
    const textBeforeCursor = message.slice(0, cursorPos)
    const textAfterCursor = message.slice(cursorPos)

    const atIndex = textBeforeCursor.lastIndexOf("@")
    const newText = textBeforeCursor.slice(0, atIndex) + `@${agentName} ` + textAfterCursor

    setMessage(newText)
    setShowMentions(false)
    setMentionSearch("")

    setTimeout(() => {
      const newCursorPos = atIndex + agentName.length + 2
      textarea.setSelectionRange(newCursorPos, newCursorPos)
      textarea.focus()
    }, 0)
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setMessage(value)

    const cursorPos = e.target.selectionStart
    const textBeforeCursor = value.slice(0, cursorPos)

    const atIndex = textBeforeCursor.lastIndexOf("@")
    const spaceAfterAt = textBeforeCursor.slice(atIndex).indexOf(" ")

    if (atIndex !== -1 && spaceAfterAt === -1 && cursorPos - atIndex <= 20) {
      const searchTerm = textBeforeCursor.slice(atIndex + 1)
      setMentionSearch(searchTerm)
      setShowMentions(true)
      setSelectedMentionIndex(0)
    } else {
      setShowMentions(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentions && filteredAgents.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault()
        setSelectedMentionIndex((prev) => (prev + 1) % filteredAgents.length)
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setSelectedMentionIndex((prev) => (prev - 1 + filteredAgents.length) % filteredAgents.length)
      } else if (e.key === "Tab" || e.key === "Enter") {
        if (showMentions) {
          e.preventDefault()
          insertMention(filteredAgents[selectedMentionIndex].name)
        }
      } else if (e.key === "Escape") {
        e.preventDefault()
        setShowMentions(false)
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      // Handle send
    }
  }

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        mentionDropdownRef.current &&
        !mentionDropdownRef.current.contains(event.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(event.target as Node)
      ) {
        setShowMentions(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="flex flex-col h-full bg-background">
      {sidebarCollapsed && (
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="w-8 h-8 text-foreground hover:bg-accent"
          >
            <Menu className="w-5 h-5" />
          </Button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className="flex gap-3">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg agent-avatar ${msg.agent.colorClass}`}
            >
              {msg.agent.avatar}
            </div>

            <div className="flex-1 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">{msg.agent.name}</div>

              {msg.type === "thinking" && (
                <div className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">{msg.content}</div>
              )}

              {msg.type === "question" && (
                <div className={`rounded-lg p-4 relative agent-question ${msg.agent.colorClass}`}>
                  <div className="text-sm leading-relaxed whitespace-pre-wrap pr-8">
                    {msg.expanded ? msg.content : msg.content.slice(0, 100) + "..."}
                  </div>
                  <button
                    onClick={() => toggleExpand(msg.id)}
                    className="absolute top-4 right-4 hover:opacity-80 transition-opacity"
                  >
                    {msg.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              )}

              {msg.type === "reply" && (
                <div className="rounded-lg p-4 bg-[#1a1a1a] border border-white/10">
                  <div className="text-sm text-white leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className={`p-1 m-4 rounded-xl relative agent-input-border ${activeAgent.colorClass}`}>
        {showMentions && filteredAgents.length > 0 && (
          <div
            ref={mentionDropdownRef}
            className="absolute bottom-full left-0 right-0 mb-2 mx-1 bg-card border border-border rounded-lg shadow-lg overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2 border-b border-border">
              <span className="text-sm font-medium text-foreground">Group Members</span>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 text-xs bg-accent rounded">Tab</kbd>
                to select
              </span>
            </div>
            <div className="max-h-[240px] overflow-y-auto">
              {filteredAgents.map((agent, index) => (
                <button
                  key={agent.name}
                  onClick={() => insertMention(agent.name)}
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-accent/50 transition-colors ${
                    index === selectedMentionIndex ? "bg-accent/50" : ""
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 agent-avatar ${agent.colorClass}`}
                  >
                    {agent.avatar}
                  </div>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium text-foreground">{agent.name}</div>
                    <div className="text-xs text-muted-foreground">{agent.role}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="bg-card rounded-lg p-4">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Press Enter to send requests anytime - we'll notice."
            className="min-h-[80px] resize-none bg-transparent border-0 focus-visible:ring-0 text-sm text-foreground placeholder:text-muted-foreground p-0"
          />
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
            <div className="flex gap-2">
              <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent">
                <Plus className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent">
                <Shuffle className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent">
                <User className="w-4 h-4" />
              </Button>
            </div>
            <Button size="icon" className={`h-8 w-8 rounded-lg agent-question ${activeAgent.colorClass}`}>
              <ArrowUp className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
