import { createFileRoute } from "@tanstack/react-router"
import { useRef, useState, useCallback } from "react"
import { ChatPanelWS } from "@/components/chat/chat-panel-ws"
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
  const chatWidthRef = useRef(40) // Use ref for smooth drag
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [sidebarHovered, setSidebarHovered] = useState(false)
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false)
  const sendMessageRef = useRef<((params: { content: string; author_type?: 'user' | 'agent' }) => boolean) | null>(null)
  const [kanbanData, setKanbanData] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<string | null>(null)
  // Track agent statuses from WebSocket for avatar display
  const [agentStatuses, setAgentStatuses] = useState<Map<string, { status: string; lastUpdate: string }>>(new Map())
  // Track selected artifact for viewing
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  // Track selected file for viewing
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  // Callback to insert @mention in chat
  const insertMentionRef = useRef<((agentName: string) => void) | null>(null)

  const handleOpenArtifact = (artifactId: string) => {
    console.log('[Workspace] Opening artifact:', artifactId)
    setSelectedArtifactId(artifactId)
    setActiveTab('file') // Switch to file tab to show artifact viewer
  }

  const handleOpenFile = (filePath: string) => {
    console.log('[Workspace] Opening file:', filePath)
    setSelectedFile(filePath)
    setActiveTab('file') // Switch to file tab
  }

  const handleMessageAgent = (agentName: string) => {
    console.log('[Workspace] Messaging agent:', agentName)
    // Expand chat if collapsed
    if (chatCollapsed) {
      setChatCollapsed(false)
    }
    // Insert @mention via the ref callback
    if (insertMentionRef.current) {
      insertMentionRef.current(agentName)
    }
  }

  // Stable resize handler - directly manipulates DOM for smooth dragging
  const handleResize = useCallback((delta: number) => {
    const newWidth = chatWidthRef.current + (delta / window.innerWidth) * 100
    chatWidthRef.current = Math.max(20, Math.min(80, newWidth))
    
    // Directly update DOM for smooth performance (no React re-render)
    if (chatContainerRef.current) {
      chatContainerRef.current.style.width = `${chatWidthRef.current}%`
    }
  }, [])

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
                ref={chatContainerRef}
                className="flex flex-col overflow-hidden"
                style={{ width: `${chatWidthRef.current}%` }}
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
                  onOpenArtifact={handleOpenArtifact}
                  onOpenFile={handleOpenFile}
                  onInsertMentionReady={(fn) => {
                    insertMentionRef.current = fn
                  }}
                />
              </div>

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
              selectedArtifactId={selectedArtifactId}
              initialSelectedFile={selectedFile}
              onResize={handleResize}
              onMessageAgent={handleMessageAgent}
            />
          </div>
        </div>
      </div>
  )
}
