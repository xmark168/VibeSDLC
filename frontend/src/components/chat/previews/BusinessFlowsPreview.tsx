interface FlowData {
  name: string
  description: string
  steps?: string[]
  actors?: string[]
}

interface BusinessFlowsPreviewProps {
  flows: FlowData[]
}

export function BusinessFlowsPreview({ flows }: BusinessFlowsPreviewProps) {
  if (!flows || !Array.isArray(flows)) return null

  return (
    <div className="space-y-4 max-h-[400px] overflow-y-auto">
      {flows.map((flow, index) => (
        <div key={index} className="border rounded-lg p-4">
          <h4 className="font-semibold text-sm text-foreground">{flow.name}</h4>
          <p className="text-xs text-muted-foreground mt-1">{flow.description}</p>
          {flow.steps && flow.steps.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-foreground">Các bước:</p>
              <ol className="list-decimal list-inside text-xs mt-1 space-y-1 text-muted-foreground">
                {flow.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}
          {flow.actors && flow.actors.length > 0 && (
            <p className="text-xs text-muted-foreground mt-2">
              <strong className="text-foreground">Actors:</strong> {flow.actors.join(', ')}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
