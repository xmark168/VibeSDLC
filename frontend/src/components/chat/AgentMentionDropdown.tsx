/**
 * AgentMentionDropdown - Agent mention selection dropdown
 * 
 * Features:
 * - Filtered agent list based on search
 * - Keyboard navigation (arrow keys + Enter)
 * - Click to select
 * - Positioned near cursor
 */

import { useEffect, useRef, type KeyboardEvent } from 'react'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'

export interface Agent {
  id: string
  name: string
  role: string
  avatar: string
}

export interface AgentMentionDropdownProps {
  /** List of agents to display */
  agents: Agent[]
  /** Current search query */
  searchQuery: string
  /** Currently selected index */
  selectedIndex: number
  /** Select handler */
  onSelect: (agent: Agent) => void
  /** Close dropdown handler */
  onClose: () => void
  /** Navigate up/down handler */
  onNavigate?: (direction: 'up' | 'down') => void
  /** Dropdown position */
  position?: { top: number; left: number }
}

export function AgentMentionDropdown({
  agents,
  searchQuery,
  selectedIndex,
  onSelect,
  onClose,
  onNavigate,
  position,
}: AgentMentionDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Filter agents based on search query
  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.role.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (!onNavigate) return

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        onNavigate('up')
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        onNavigate('down')
      } else if (e.key === 'Enter' && filteredAgents[selectedIndex]) {
        e.preventDefault()
        onSelect(filteredAgents[selectedIndex])
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [filteredAgents, selectedIndex, onSelect, onClose, onNavigate])

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = dropdownRef.current?.querySelector(
      `[data-index="${selectedIndex}"]`
    )
    selectedElement?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (filteredAgents.length === 0) {
    return null
  }

  return (
    <Card
      ref={dropdownRef}
      className="absolute z-50 w-80 shadow-lg"
      style={position ? { top: position.top, left: position.left } : undefined}
    >
      <div className="p-2">
        <div className="text-xs text-muted-foreground mb-2 px-2">
          Select an agent to mention
        </div>
        <ScrollArea className="max-h-60">
          {filteredAgents.map((agent, index) => (
            <button
              key={agent.id}
              data-index={index}
              onClick={() => onSelect(agent)}
              className={`
                w-full text-left px-3 py-2 rounded-md transition-colors
                flex items-center gap-3
                ${index === selectedIndex
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent/50'
                }
              `}
            >
              {/* Avatar */}
              <span className="text-2xl">{agent.avatar}</span>
              
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{agent.name}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {agent.role}
                </div>
              </div>

              {/* Selected indicator */}
              {index === selectedIndex && (
                <span className="text-xs text-muted-foreground">
                  ↵ Enter
                </span>
              )}
            </button>
          ))}
        </ScrollArea>
      </div>
    </Card>
  )
}
