
import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Menu,
  ChevronDown,
  ChevronUp,
  ArrowUp,
  Copy,
  Check,
  Paperclip,
  X,
  FileText,
  ImageIcon,
  Download,
  File,
  Moon,
  Sun,
  AtSign,
  PanelRightClose,
  PanelLeftClose,
  ChevronsLeft,
} from "lucide-react"
import { TechStackDialog } from "./tech-stack-dialog"

interface ChatPanelProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
  onCollapse: () => void
  onSidebarHover: (hovered: boolean) => void
}

type MessageType = "thinking" | "question" | "reply"

interface Message {
  id: string
  agent: {
    name: string
    avatar: string
  }
  type: MessageType
  content: string
  expanded?: boolean
  attachments?: AttachedFile[]
}

interface AttachedFile {
  id: string
  name: string
  size: number
  type: string
  url?: string
}

const AGENTS = [
  { name: "Mike", role: "Team Leader", avatar: "👨‍💼" },
  { name: "Emma", role: "Product Manager", avatar: "👩‍💼" },
  { name: "Bob", role: "Architect", avatar: "👨‍🔧" },
  { name: "Alex", role: "Engineer", avatar: "👨‍💻" },
  { name: "Developer", role: "Developer", avatar: "🔧" },
  { name: "Tester", role: "Tester", avatar: "🧪" },
]

export function ChatPanel({ sidebarCollapsed, onToggleSidebar, onCollapse, onSidebarHover }: ChatPanelProps) {
  const [message, setMessage] = useState("")
  const [showMentions, setShowMentions] = useState(false)
  const [mentionSearch, setMentionSearch] = useState("")
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0)
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [theme, setTheme] = useState<"light" | "dark">("dark")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const mentionDropdownRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const prevMessagesLengthRef = useRef(0)

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      agent: {
        name: "Developer",
        avatar: "🔧",
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
      },
      type: "reply",
      content: "Race m",
    },
    {
      id: "4",
      agent: {
        name: "Tester",
        avatar: "🧪",
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

  const handleSend = () => {
    // Don't send if message is empty (or only whitespace) and no files attached
    if (!message.trim() && attachedFiles.length === 0) return

    // Create new message with attachments
    const newMessage: Message = {
      id: Date.now().toString(),
      agent: {
        name: "User",
        avatar: "👤",
      },
      type: "reply",
      content: message.trim(),
      attachments: attachedFiles.length > 0 ? [...attachedFiles] : undefined,
    }

    // Add message to chat
    setMessages((prev) => [...prev, newMessage])

    // Clear input and files
    setMessage("")
    setAttachedFiles([])

    // Focus back on textarea
    setTimeout(() => {
      textareaRef.current?.focus()
    }, 0)
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
      handleSend()
    }
  }

  const copyToClipboard = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageId(messageId)
      setTimeout(() => setCopiedMessageId(null), 2000)
    } catch (err) {
      console.error("Failed to copy:", err)
    }
  }

  const formatTimestamp = (id: string) => {
    const date = new Date(Number.parseInt(id))
    const hours = date.getHours()
    const minutes = date.getMinutes().toString().padStart(2, "0")
    const ampm = hours >= 12 ? "PM" : "AM"
    const displayHours = hours % 12 || 12
    const month = date.toLocaleString("en-US", { month: "short" })
    const day = date.getDate().toString().padStart(2, "0")
    return `${displayHours}:${minutes} ${ampm} on ${month} ${day}`
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    const newFiles: AttachedFile[] = Array.from(files).map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      url: URL.createObjectURL(file),
    }))

    setAttachedFiles((prev) => [...prev, ...newFiles])
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const removeFile = (fileId: string) => {
    setAttachedFiles((prev) => {
      const file = prev.find((f) => f.id === fileId)
      if (file?.url) {
        URL.revokeObjectURL(file.url)
      }
      return prev.filter((f) => f.id !== fileId)
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B"
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
    return (bytes / (1024 * 1024)).toFixed(1) + " MB"
  }

  const getFileIcon = (type: string) => {
    if (type.startsWith("image/")) return <ImageIcon className="w-4 h-4" />
    return <FileText className="w-4 h-4" />
  }

  const renderAttachment = (file: AttachedFile) => {
    const isImage = file.type.startsWith("image/")
    const isPDF = file.type === "application/pdf"

    if (isImage && file.url) {
      return (
        <div key={file.id} className="relative group">
          <img
            src={file.url || "/placeholder.svg"}
            alt={file.name}
            className="max-w-sm max-h-64 rounded-lg border border-border object-cover"
          />
          <a
            href={file.url}
            download={file.name}
            className="absolute top-2 right-2 p-2 bg-background/80 hover:bg-background/90 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity border border-border"
            title="Download"
          >
            <Download className="w-4 h-4 text-foreground" />
          </a>
        </div>
      )
    }

    return (
      <a
        key={file.id}
        href={file.url}
        download={file.name}
        className="flex items-center gap-3 px-4 py-3 bg-muted hover:bg-muted/80 rounded-lg border border-border transition-colors group max-w-sm"
      >
        <div className="p-2 bg-background rounded">
          {isPDF ? <FileText className="w-5 h-5 text-red-500" /> : <File className="w-5 h-5 text-blue-500" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-foreground font-medium truncate">{file.name}</div>
          <div className="text-xs text-muted-foreground">{formatFileSize(file.size)}</div>
        </div>
        <Download className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0" />
      </a>
    )
  }

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light"
    setTheme(newTheme)
    localStorage.setItem("theme", newTheme)
    document.documentElement.classList.toggle("dark", newTheme === "dark")
  }

  const triggerMention = () => {
    const textarea = textareaRef.current
    if (!textarea) return

    const cursorPos = textarea.selectionStart
    const newMessage = message.slice(0, cursorPos) + "@" + message.slice(cursorPos)

    setMessage(newMessage)
    setShowMentions(true)
    setMentionSearch("")
    setSelectedMentionIndex(0)

    setTimeout(() => {
      textarea.focus()
      const newCursorPos = cursorPos + 1
      textarea.setSelectionRange(newCursorPos, newCursorPos)
    }, 0)
  }

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as "light" | "dark" | null
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    const initialTheme = savedTheme || (prefersDark ? "dark" : "light")

    setTheme(initialTheme)
    document.documentElement.classList.toggle("dark", initialTheme === "dark")
  }, [])

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

  useEffect(() => {
    // Only auto-scroll if a new message was added, not when updating existing messages
    if (messagesContainerRef.current && messages.length > prevMessagesLengthRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
    prevMessagesLengthRef.current = messages.length
  }, [messages])

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
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="w-8 h-8 text-foreground hover:bg-accent"
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
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
        <div className="flex items-center justify-end gap-2 px-3 py-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="w-8 h-8 text-foreground hover:bg-accent"
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
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
      )}

      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((msg) => {
          const isUserMessage = msg.agent.name === "User"

          if (isUserMessage) {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[70%]">
                  {msg.content && (
                    <div className="space-y-1.5">
                      <div className="rounded-lg px-3 py-2 bg-muted w-fit ml-auto">
                        <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">{msg.content}</div>
                      </div>
                      <div className="flex items-center justify-end gap-2 px-1">
                        <span className="text-xs text-muted-foreground">{formatTimestamp(msg.id)}</span>
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
                  )}
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex flex-col gap-2">{msg.attachments.map((file) => renderAttachment(file))}</div>
                  )}
                </div>
              </div>
            )
          }

          return (
            <div key={msg.id} className="flex gap-3">
              <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg bg-muted">
                {msg.agent.avatar}
              </div>

              <div className="flex-1 space-y-2">
                <div className="text-xs font-medium text-muted-foreground">{msg.agent.name}</div>

                {msg.type === "thinking" && (
                  <div className="space-y-1.5">
                    <div className="text-sm text-foreground/80 leading-loose whitespace-pre-wrap">{msg.content}</div>
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-xs text-muted-foreground">{formatTimestamp(msg.id)}</span>
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
                )}

                {msg.type === "question" && (
                  <div className="space-y-1.5">
                    <div className="rounded-lg px-3 py-2 bg-muted w-fit">
                      <div className="text-sm leading-loose whitespace-pre-wrap text-foreground">
                        {msg.expanded ? msg.content : msg.content.slice(0, 100) + "..."}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-xs text-muted-foreground">{formatTimestamp(msg.id)}</span>
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
                      <button
                        onClick={() => toggleExpand(msg.id)}
                        className="p-1 hover:bg-accent rounded transition-colors"
                        title={msg.expanded ? "Collapse" : "Expand"}
                      >
                        {msg.expanded ? (
                          <ChevronUp className="w-3.5 h-3.5 text-foreground" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5 text-foreground" />
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {msg.type === "reply" && !isUserMessage && (
                  <div className="space-y-3">
                    {msg.content && (
                      <div className="space-y-1.5">
                        <div className="rounded-lg px-3 py-2 bg-muted border border-border">
                          <div className="text-sm text-foreground leading-loose whitespace-pre-wrap">
                            {msg.content}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 px-1">
                          <span className="text-xs text-muted-foreground">{formatTimestamp(msg.id)}</span>
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
                    )}
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex flex-col gap-2">{msg.attachments.map((file) => renderAttachment(file))}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="p-2 m-4 rounded-4xl relative bg-muted">
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
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-accent/50 transition-colors ${index === selectedMentionIndex ? "bg-accent/50" : ""
                    }`}
                >
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 bg-muted">
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

        <div className="bg-transparent rounded-4xl p-1 border-0">
          {attachedFiles.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg text-sm group hover:bg-muted/80 transition-colors"
                >
                  {getFileIcon(file.type)}
                  <div className="flex flex-col min-w-0">
                    <span className="text-foreground truncate max-w-[150px]">{file.name}</span>
                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                  </div>
                  <button
                    onClick={() => removeFile(file.id)}
                    className="ml-1 p-1 hover:bg-background rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Press Enter to send requests anytime - we'll notice."
            className="min-h-[40px] resize-none bg-transparent border-0 text-sm text-foreground placeholder:text-muted-foreground p-1 focus-visible:ring-0 focus-visible:ring-transparent focus-visible:ring-offset-0"
          />
          <div className="flex items-center justify-between pt-3">
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 hover:bg-accent"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent" onClick={triggerMention}>
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
            <Button size="icon" className="h-8 w-8 rounded-lg bg-primary hover:bg-primary/90" onClick={handleSend}>
              <ArrowUp className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
