import { ChatPanel } from '@/components/chat/chat-panel'
import { ResizableHandle } from '@/components/chat/resizable-handle'
import { Sidebar } from '@/components/chat/sidebar'
import { WorkspacePanel } from '@/components/chat/workspace-panel'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from "react"
export const Route = createFileRoute('/chat/$chatId')({
  component: ChatPage,
})

function ChatPage() {
  const { chatId } = Route.useParams()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [chatWidth, setChatWidth] = useState(40) // percentage
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [sidebarHovered, setSidebarHovered] = useState(false)
 return (
    <div className="flex h-screen overflow-hidden bg-background relative">
      <Sidebar 
      collapsed={sidebarCollapsed} 
      onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
      hovered={sidebarHovered}
        onHoverChange={setSidebarHovered}
      />

      <div className="flex flex-1 overflow-hidden">
        {!chatCollapsed && (
          <>
            <div className="flex flex-col overflow-hidden border-r border-border" style={{ width: `${chatWidth}%` }}>
              <ChatPanel
                sidebarCollapsed={sidebarCollapsed}
                onToggleSidebar={() => setSidebarCollapsed(false)}
                onCollapse={() => setChatCollapsed(true)}
                onSidebarHover = {setSidebarHovered}
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
          <WorkspacePanel chatCollapsed={chatCollapsed} onExpandChat={() => setChatCollapsed(false)} />
        </div>
      </div>
    </div>
  )
}