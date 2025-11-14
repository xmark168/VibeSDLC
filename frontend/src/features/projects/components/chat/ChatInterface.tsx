import { useState } from 'react'
import { AgentSelector } from './AgentSelector'
import { ChatMessageList } from './ChatMessageList'
import { ChatInput } from './ChatInput'
import type { AgentType, Message } from '../../types/chat'
import { MOCK_CONVERSATIONS } from '../../mocks/chatData'

export const ChatInterface = () => {
  const [selectedAgent, setSelectedAgent] = useState<AgentType | 'ALL'>('ALL')
  const [conversations, setConversations] = useState(MOCK_CONVERSATIONS)
  const [isTyping, setIsTyping] = useState(false)

  const currentMessages = conversations[selectedAgent] || []

  const handleSendMessage = (content: string) => {
    // Create new user message
    const newUserMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }

    // Add user message to conversation
    setConversations((prev) => ({
      ...prev,
      [selectedAgent]: [...(prev[selectedAgent] || []), newUserMessage],
    }))

    // Simulate agent typing and response
    setIsTyping(true)

    // Mock agent response after 1.5 seconds
    setTimeout(() => {
      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        role: 'agent',
        content: generateMockResponse(content),
        agentType: selectedAgent !== 'ALL' ? selectedAgent : 'FLOW_MANAGER',
        timestamp: new Date(),
      }

      setConversations((prev) => ({
        ...prev,
        [selectedAgent]: [...(prev[selectedAgent] || []), agentMessage],
      }))

      setIsTyping(false)
    }, 1500)
  }

  const generateMockResponse = (userMessage: string): string => {
    // Simple mock response generator
    const lowerMessage = userMessage.toLowerCase()

    if (lowerMessage.includes('create') || lowerMessage.includes('add')) {
      return "I'll help you create that. In a real implementation, I would process your request and create the necessary items in the project board."
    }

    if (lowerMessage.includes('status') || lowerMessage.includes('progress')) {
      return 'The project is progressing well. We have several stories in progress and the team is meeting the sprint goals. Would you like a detailed breakdown?'
    }

    if (lowerMessage.includes('help') || lowerMessage.includes('how')) {
      return "I'm here to help! I can assist with:\n\n• Creating and managing stories\n• Checking project status\n• Analyzing workflow metrics\n• Prioritizing backlog items\n\nWhat would you like to do?"
    }

    return "I understand your request. In the full implementation, I would process this and provide a detailed response based on the project data and AI agent capabilities."
  }

  return (
    <div className="flex flex-col h-full bg-white border-2 border-gray-200 rounded-2xl overflow-hidden shadow-lg">
      {/* Agent Selector */}
      <AgentSelector selectedAgent={selectedAgent} onSelectAgent={setSelectedAgent} />

      {/* Message List */}
      <ChatMessageList messages={currentMessages} isTyping={isTyping} />

      {/* Input */}
      <ChatInput onSendMessage={handleSendMessage} disabled={isTyping} />
    </div>
  )
}
