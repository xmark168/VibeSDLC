import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Check, X, Download, Copy, Loader2 } from 'lucide-react'
import type { Artifact } from '@/apis/artifacts'
import { artifactsApi } from '@/apis/artifacts'
import { toast } from "@/lib/toast"

interface ArtifactViewerProps {
  artifact: Artifact
  onClose?: () => void
}

export function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'json'>('preview')
  const [isUpdating, setIsUpdating] = useState(false)

  const handleApprove = async () => {
    setIsUpdating(true)
    try {
      await artifactsApi.updateArtifactStatus(artifact.id, 'approved')
      toast.success('Artifact approved')
    } catch (error) {
      toast.error('Failed to approve artifact')
      console.error(error)
    } finally {
      setIsUpdating(false)
    }
  }

  const handleReject = async () => {
    setIsUpdating(true)
    try {
      await artifactsApi.updateArtifactStatus(artifact.id, 'rejected')
      toast.success('Artifact rejected')
    } catch (error) {
      toast.error('Failed to reject artifact')
      console.error(error)
    } finally {
      setIsUpdating(false)
    }
  }

  const handleCopy = () => {
    const content = JSON.stringify(artifact.content, null, 2)
    navigator.clipboard.writeText(content)
    toast.success('Copied to clipboard')
  }

  const handleDownload = () => {
    const content = JSON.stringify(artifact.content, null, 2)
    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.title.replace(/\s+/g, '_')}_v${artifact.version}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Downloaded')
  }

  const renderPreview = () => {
    const content = artifact.content

    // Render based on artifact type
    switch (artifact.artifact_type) {
      case 'analysis':
      case 'prd':
        return (
          <div className="p-6 space-y-6">
            {content.title && (
              <div>
                <h2 className="text-2xl font-bold mb-2">{content.title}</h2>
              </div>
            )}

            {content.overview && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Overview</h3>
                <p className="text-sm text-muted-foreground">{content.overview}</p>
              </div>
            )}

            {content.goals && content.goals.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Goals</h3>
                <ul className="list-disc list-inside space-y-1">
                  {content.goals.map((goal: string, i: number) => (
                    <li key={i} className="text-sm">{goal}</li>
                  ))}
                </ul>
              </div>
            )}

            {content.requirements && content.requirements.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Requirements</h3>
                <div className="space-y-3">
                  {content.requirements.map((req: any, i: number) => (
                    <div key={i} className="border rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded">
                          {req.id}
                        </span>
                        <h4 className="font-semibold text-sm">{req.title}</h4>
                      </div>
                      <p className="text-sm text-muted-foreground">{req.description}</p>
                      <div className="flex gap-2 mt-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          req.priority === 'high' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                          req.priority === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' :
                          'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                        }`}>
                          {req.priority}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-muted">
                          {req.type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {content.risks && content.risks.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Risks</h3>
                <ul className="list-disc list-inside space-y-1">
                  {content.risks.map((risk: string, i: number) => (
                    <li key={i} className="text-sm text-red-600 dark:text-red-400">{risk}</li>
                  ))}
                </ul>
              </div>
            )}

            {content.next_steps && content.next_steps.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Next Steps</h3>
                <ol className="list-decimal list-inside space-y-1">
                  {content.next_steps.map((step: string, i: number) => (
                    <li key={i} className="text-sm">{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {content.full_analysis && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Full Analysis</h3>
                <div className="text-sm whitespace-pre-wrap bg-muted p-4 rounded-lg">
                  {content.full_analysis}
                </div>
              </div>
            )}
          </div>
        )

      default:
        return (
          <div className="p-6">
            <pre className="text-sm whitespace-pre-wrap">
              {JSON.stringify(content, null, 2)}
            </pre>
          </div>
        )
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div>
          <h3 className="font-semibold">{artifact.title}</h3>
          <p className="text-xs text-muted-foreground">
            Version {artifact.version} • {artifact.artifact_type} • by {artifact.agent_name}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tabs */}
          <div className="flex gap-1 mr-4">
            <Button
              size="sm"
              variant={activeTab === 'preview' ? 'default' : 'ghost'}
              onClick={() => setActiveTab('preview')}
            >
              Preview
            </Button>
            <Button
              size="sm"
              variant={activeTab === 'json' ? 'default' : 'ghost'}
              onClick={() => setActiveTab('json')}
            >
              JSON
            </Button>
          </div>

          {/* Actions */}
          {artifact.status === 'draft' && (
            <>
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleApprove}
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-1" />
                )}
                Approve
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleReject}
                disabled={isUpdating}
              >
                <X className="w-4 h-4 mr-1" />
                Reject
              </Button>
            </>
          )}

          <Button size="sm" variant="ghost" onClick={handleCopy}>
            <Copy className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="ghost" onClick={handleDownload}>
            <Download className="w-4 h-4" />
          </Button>

          {onClose && (
            <Button size="sm" variant="ghost" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'preview' ? (
          renderPreview()
        ) : (
          <pre className="p-4 text-xs overflow-auto">
            {JSON.stringify(artifact.content, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
