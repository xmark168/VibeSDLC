import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Play, Loader2, RefreshCw, ExternalLink, Monitor, Square, CheckCircle2, XCircle, Lock, Copy, ArrowRight } from "lucide-react"
import { toast } from "@/lib/toast"

interface LogEntry {
  message: string
  status: "running" | "success" | "error"
  timestamp: Date
}

interface AppViewerProps {
  projectId?: string
}

export function AppViewer({ projectId }: AppViewerProps) {
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [runningPort, setRunningPort] = useState<number | null>(null)
  const [hasWorkspace, setHasWorkspace] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [currentUrl, setCurrentUrl] = useState<string>("")
  const [inputUrl, setInputUrl] = useState<string>("")
  const iframeRef = useRef<HTMLIFrameElement>(null)

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
      }
    }
    
    fetchStatus()
  }, [projectId])

  // Listen for WebSocket updates
  useEffect(() => {
    const handleDevServer = (event: CustomEvent) => {
      if (event.detail.project_id === projectId) {
        setRunningPort(event.detail.running_port)
        if (event.detail.running_port) {
          // Clear logs when server is ready
          setLogs([])
        }
      }
    }
    
    const handleDevServerLog = (event: CustomEvent) => {
      if (event.detail.project_id === projectId) {
        setLogs(prev => {
          // Update last log if same status "running", otherwise add new
          const newLog: LogEntry = {
            message: event.detail.message,
            status: event.detail.status,
            timestamp: new Date()
          }
          
          // If last log was "running" and new one is different message, update it
          if (prev.length > 0 && prev[prev.length - 1].status === "running" && event.detail.status !== "running") {
            return [...prev.slice(0, -1), newLog]
          }
          
          // Replace running log with new running log, or add new log
          if (prev.length > 0 && prev[prev.length - 1].status === "running" && event.detail.status === "running") {
            return [...prev.slice(0, -1), newLog]
          }
          
          return [...prev, newLog]
        })
      }
    }
    
    window.addEventListener('project_dev_server', handleDevServer as EventListener)
    window.addEventListener('dev_server_log', handleDevServerLog as EventListener)
    return () => {
      window.removeEventListener('project_dev_server', handleDevServer as EventListener)
      window.removeEventListener('dev_server_log', handleDevServerLog as EventListener)
    }
  }, [projectId])

  // Sync URL state when port changes
  useEffect(() => {
    if (runningPort) {
      const baseUrl = `http://localhost:${runningPort}`
      setCurrentUrl(baseUrl)
      setInputUrl(baseUrl)
    }
  }, [runningPort])

  // Listen for navigation events from iframe via postMessage
  // Note: Cannot directly access iframe.contentWindow.location due to cross-origin restrictions
  // even though both are localhost (different ports = different origins)
  useEffect(() => {
    if (!runningPort) return

    // Request iframe to send its current URL periodically
    const requestIframeUrl = () => {
      try {
        iframeRef.current?.contentWindow?.postMessage({ type: 'REQUEST_URL' }, `http://localhost:${runningPort}`)
      } catch (error) {
        // Silently fail if iframe not ready
      }
    }

    // Listen for URL updates from iframe
    const handleMessage = (event: MessageEvent) => {
      // Verify message is from our iframe
      if (event.origin === `http://localhost:${runningPort}` && event.data?.type === 'URL_UPDATE') {
        const iframeUrl = event.data.url
        setCurrentUrl(prev => {
          if (iframeUrl && iframeUrl !== prev) {
            setInputUrl(iframeUrl)
            return iframeUrl
          }
          return prev
        })
      }
    }

    window.addEventListener('message', handleMessage)

    // Request URL immediately and then periodically
    const initialTimer = setTimeout(requestIframeUrl, 500)
    const interval = setInterval(requestIframeUrl, 1000)
    
    return () => {
      window.removeEventListener('message', handleMessage)
      clearTimeout(initialTimer)
      clearInterval(interval)
    }
  }, [runningPort])

  const handleStartDevServer = async () => {
    if (!projectId) {
      toast.error("No project selected")
      return
    }
    
    setIsStarting(true)
    setLogs([]) // Clear previous logs
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
      toast.error('Failed to stop dev server')
    } finally {
      setIsStopping(false)
    }
  }

  const handleRefresh = () => {
    setIframeKey(prev => prev + 1)
  }

  const handleNavigate = () => {
    // Validate URL starts with localhost
    if (inputUrl.startsWith(`http://localhost:${runningPort}`)) {
      setCurrentUrl(inputUrl)
      setIframeKey(prev => prev + 1) // Force iframe reload
    } else {
      toast.error(`URL must start with http://localhost:${runningPort}`)
      setInputUrl(currentUrl) // Reset to current URL
    }
  }

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(currentUrl)
    toast.success('URL copied to clipboard')
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
              <a href={currentUrl} target="_blank" rel="noopener noreferrer">
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

        {/* Browser-like URL bar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/10">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Lock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            
            <Input
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNavigate()
              }}
              className="flex-1 bg-background border-muted font-mono text-sm h-8 px-3"
              placeholder={`http://localhost:${runningPort}`}
            />
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNavigate}
              title="Navigate"
              className="flex-shrink-0"
            >
              <ArrowRight className="w-4 h-4" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopyUrl}
              title="Copy URL"
              className="flex-shrink-0"
            >
              <Copy className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        {/* Iframe */}
        <div className="flex-1 overflow-hidden">
          {currentUrl && (
            <iframe
              ref={iframeRef}
              key={iframeKey}
              src={currentUrl}
              className="w-full h-full border-0"
              title="App Preview"
              onLoad={() => {
                // Sync URL when iframe finishes loading
                try {
                  if (iframeRef.current?.contentWindow?.location) {
                    const iframeUrl = iframeRef.current.contentWindow.location.href
                    setCurrentUrl(prev => {
                      if (iframeUrl && iframeUrl !== prev) {
                        setInputUrl(iframeUrl)
                        return iframeUrl
                      }
                      return prev
                    })
                  }
                } catch {
                  // Cannot access iframe URL (cross-origin)
                }
              }}
            />
          )}
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
          <>
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
            
            {/* Logs display */}
            {isStarting && logs.length > 0 && (
              <div className="w-full max-w-sm mt-4 space-y-2">
                {logs.map((log, index) => (
                  <div 
                    key={index} 
                    className="flex items-center gap-2 text-sm"
                  >
                    {log.status === "running" && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    )}
                    {log.status === "success" && (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    )}
                    {log.status === "error" && (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className={
                      log.status === "running" ? "text-blue-600" :
                      log.status === "success" ? "text-green-600" :
                      "text-red-600"
                    }>
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
