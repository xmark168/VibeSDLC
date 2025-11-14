import { ChevronDown, Workflow, Briefcase, Code, Bug, MessageSquare } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.jsx'
import type { AgentType } from '../../types/chat'
import { AGENT_INFO } from '../../types/chat'

interface AgentSelectorProps {
  selectedAgent: AgentType | 'ALL'
  onSelectAgent: (agent: AgentType | 'ALL') => void
}

const AGENT_ICONS: Record<AgentType | 'ALL', React.ComponentType<any>> = {
  ALL: MessageSquare,
  FLOW_MANAGER: Workflow,
  BUSINESS_ANALYST: Briefcase,
  DEVELOPER: Code,
  TESTER: Bug,
}

export const AgentSelector = ({ selectedAgent, onSelectAgent }: AgentSelectorProps) => {
  const SelectedIcon = AGENT_ICONS[selectedAgent]

  const getAgentDisplay = (agentType: AgentType | 'ALL') => {
    if (agentType === 'ALL') {
      return { name: 'All Agents', color: '#6b7280' }
    }
    return AGENT_INFO[agentType]
  }

  return (
    <div className="border-b-2 border-gray-200 bg-white p-4">
      <label className="text-sm font-semibold text-gray-700 mb-2 block">Chat with</label>
      <Select value={selectedAgent} onValueChange={(value) => onSelectAgent(value as AgentType | 'ALL')}>
        <SelectTrigger className="h-12 border-2 border-gray-200 hover:border-gray-300 focus:border-blue-500 transition-colors rounded-xl">
          <div className="flex items-center gap-3 w-full">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: getAgentDisplay(selectedAgent).color + '20' }}
            >
              <SelectedIcon
                className="w-5 h-5"
                style={{ color: getAgentDisplay(selectedAgent).color }}
              />
            </div>
            <div className="flex-1 text-left">
              <SelectValue>
                <span className="font-semibold text-gray-900">{getAgentDisplay(selectedAgent).name}</span>
              </SelectValue>
            </div>
            <ChevronDown className="h-4 w-4 text-gray-500" />
          </div>
        </SelectTrigger>

        <SelectContent className="rounded-xl border-2">
          {/* All Agents Option */}
          <SelectItem value="ALL" className="cursor-pointer h-14">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <div className="font-semibold text-gray-900">All Agents</div>
                <div className="text-xs text-gray-500">General project assistant</div>
              </div>
            </div>
          </SelectItem>

          {/* Individual Agents */}
          {(Object.keys(AGENT_INFO) as AgentType[]).map((agentType) => {
            const info = AGENT_INFO[agentType]
            const Icon = AGENT_ICONS[agentType]
            return (
              <SelectItem key={agentType} value={agentType} className="cursor-pointer h-14">
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: info.color + '20' }}
                  >
                    <Icon className="w-5 h-5" style={{ color: info.color }} />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">{info.name}</div>
                    <div className="text-xs text-gray-500">{info.description}</div>
                  </div>
                </div>
              </SelectItem>
            )
          })}
        </SelectContent>
      </Select>
    </div>
  )
}
