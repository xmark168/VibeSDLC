import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Play, Loader2, RefreshCw, ExternalLink, Monitor, Square } from "lucide-react"
import { toast } from "@/lib/toast"

interface AppViewerProps {
  projectId?: string
}

export function AppViewer({ projectId }: AppViewerProps) {
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [runningPort, setRunningPort] = useState<number | null>(null)
  const [hasWorkspace, setHasWorkspace] = useState(false)

  // Fetch initial status
  useEffect(() => {
    if (!projectId) return
    
    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('access_token')
        const response = await fetch(
          `${import.meta.env.VITE_API_URL}/api/v1/projects/${projectId}/dev-server/status`,
          {
            headers: { 'Authorization': `Bearer ${token}` },
          }
        )
        if (response.ok) {
          const data = await response.json()
          setRunningPort(data.port)
          setHasWorkspace(data.has_workspace)
        }
      } catch (error) {
        console.error('Failed to fetch dev server status:', error)
      }
    }
    
    fetchStatus()
  }, [projectId])

  // Listen for WebSocket updates
  useEffect(() => {
    const handleDevServer = (event: CustomEvent) => {
      if (event.detail.project_id === projectId) {
        setRunningPort(event.detail.running_port)
      }
    }
    
    window.addEventListener('project_dev_server', handleDevServer as EventListener)
    return () => window.removeEventListener('project_dev_server', handleDevServer as EventListener)
  }, [projectId])

  const handleStartDevServer = async () => {
    if (!projectId) {
      toast.error("No project selected")
      return
    }
    
    setIsStarting(true)
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/projects/${projectId}/dev-server/start`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setRunningPort(data.port)
        toast.success(`Dev server started on port ${data.port}`)
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to start dev server')
      }
    } catch (error) {
      console.error('Failed to start dev server:', error)
      toast.error('Failed to start dev server')
    } finally {
      setIsStarting(false)
    }
  }

  const handleStopDevServer = async () => {
    if (!projectId) return
    
    setIsStopping(true)
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/projects/${projectId}/dev-server/stop`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      )
      
      if (response.ok) {
        setRunningPort(null)
        toast.success('Dev server stopped')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to stop dev server')
      }
    } catch (error) {
      console.error('Failed to stop dev server:', error)
      toast.error('Failed to stop dev server')
    } finally {
      setIsStopping(false)
    }
  }

  const handleRefresh = () => {
    setIframeKey(prev => prev + 1)
  }

  // Show iframe if dev server is running
  if (runningPort) {
    const previewUrl = `http://localhost:${runningPort}`
    
    return (
      <div className="flex-1 flex flex-col h-full bg-background">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>Running on port {runningPort}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleRefresh} title="Refresh">
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" asChild title="Open in new tab">
              <a href={previewUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleStopDevServer}
              disabled={isStopping}
              className="text-destructive hover:text-destructive"
              title="Stop server"
            >
              {isStopping ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Square className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
        
        {/* Iframe */}
        <div className="flex-1 overflow-hidden">
          <iframe
            key={iframeKey}
            src={previewUrl}
            className="w-full h-full border-0"
            title="App Preview"
          />
        </div>
      </div>
    )
  }

  // Show start button if no dev server running
  return (
    <div className="flex-1 flex flex-col items-center justify-center h-full bg-background">
      <div className="flex flex-col items-center gap-6 text-center max-w-md">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center">
          <Monitor className="w-10 h-10 text-muted-foreground" />
        </div>
        
        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-foreground">App Preview</h3>
          <p className="text-sm text-muted-foreground">
            {hasWorkspace 
              ? "Start the dev server to preview your application"
              : "No workspace found for this project"
            }
          </p>
        </div>
        
        {hasWorkspace && projectId && (
          <Button 
            size="lg" 
            onClick={handleStartDevServer}
            disabled={isStarting}
            className="gap-2"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Dev Server
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}
