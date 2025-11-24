import { createFileRoute } from "@tanstack/react-router"
import { useRef, useState } from "react"
import { ChatPanelWS } from "@/components/chat/chat-panel-ws"
import { ResizableHandle } from "@/components/chat/resizable-handle"
import { Sidebar } from "@/components/chat/sidebar"

import { WorkspacePanel } from "@/components/chat/workspace-panel"
import { requireRole } from "@/utils/auth"

export const Route = createFileRoute("/_user/workspace/$workspaceId")({
  beforeLoad: async () => {
    await requireRole('user')
  },
  component: WorkspacePage,
})

function WorkspacePage() {
  const { workspaceId } = Route.useParams()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [chatWidth, setChatWidth] = useState(40) // percentage
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [sidebarHovered, setSidebarHovered] = useState(false)
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false)
  const sendMessageRef = useRef<((params: { content: string; author_type?: 'user' | 'agent' }) => boolean) | null>(null)
  const [kanbanData, setKanbanData] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<string | null>(null)
  // Track agent statuses from WebSocket for avatar display
  const [agentStatuses, setAgentStatuses] = useState<Map<string, { status: string; lastUpdate: string }>>(new Map())

  return (
    <div className="flex h-screen overflow-hidden bg-white relative">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          hovered={sidebarHovered}
          onHoverChange={setSidebarHovered}
        />

        <div className="flex flex-1 overflow-hidden">
          {!chatCollapsed && (
            <>
              <div
                className="flex flex-col overflow-hidden"
                style={{ width: `${chatWidth}%` }}
              >
                <ChatPanelWS
                  sidebarCollapsed={sidebarCollapsed}
                  onToggleSidebar={() => setSidebarCollapsed(false)}
                  onCollapse={() => setChatCollapsed(true)}
                  onSidebarHover={setSidebarHovered}
                  projectId={workspaceId}
                  onSendMessageReady={(sendFn) => {
                    sendMessageRef.current = sendFn
                  }}
                  onConnectionChange={setIsWebSocketConnected}
                  onKanbanDataChange={setKanbanData}
                  onActiveTabChange={setActiveTab}
                  onAgentStatusesChange={setAgentStatuses}
                />
              </div>

              <ResizableHandle
                onResize={(delta) => {
                  const newWidth = chatWidth + (delta / window.innerWidth) * 100
                  setChatWidth(Math.max(20, Math.min(80, newWidth)))
                }}
              />
            </>
          )}

          <div className="flex-1 overflow-hidden">
            <WorkspacePanel
              chatCollapsed={chatCollapsed}
              onExpandChat={() => setChatCollapsed(false)}
              kanbanData={kanbanData}
              projectId={workspaceId}
              activeTab={activeTab}
              agentStatuses={agentStatuses}
            />
          </div>
        </div>
      </div>
  )
}
