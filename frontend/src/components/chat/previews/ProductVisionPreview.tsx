interface ProductVisionPreviewProps {
  vision: any
  qualityScore?: number
  validationResult?: string
}

export function ProductVisionPreview({
  vision,
  qualityScore,
  validationResult
}: ProductVisionPreviewProps) {
  if (!vision) return null

  const {
    draft_vision_statement,
    experience_principles,
    problem_summary,
    audience_segments,
    functional_requirements,
    performance_requirements,
    security_requirements,
    ux_requirements,
    scope_capabilities,
    scope_non_goals,
    dependencies,
    risks,
    assumptions
  } = vision

  return (
    <div className="space-y-4 max-h-[500px] overflow-y-auto">
      {/* Quality Score */}
      {qualityScore !== undefined && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="text-sm">
            <strong>Quality Score:</strong>{' '}
            <span className="text-blue-700 dark:text-blue-300">
              {(qualityScore * 100).toFixed(0)}%
            </span>
            {validationResult && (
              <span className="ml-2 text-muted-foreground">- {validationResult}</span>
            )}
          </div>
        </div>
      )}

      {/* Vision Statement */}
      {draft_vision_statement && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">🌟 Vision Statement:</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap italic border-l-4 border-blue-500 pl-3">
            {draft_vision_statement}
          </p>
        </div>
      )}

      {/* Experience Principles */}
      {experience_principles && experience_principles.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">💡 Experience Principles:</h4>
          <ul className="list-disc list-inside space-y-1">
            {experience_principles.map((principle: string, idx: number) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {principle}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Problem Summary */}
      {problem_summary && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">🎯 Problem Summary:</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{problem_summary}</p>
        </div>
      )}

      {/* Audience Segments */}
      {audience_segments && audience_segments.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            👥 Audience Segments ({audience_segments.length}):
          </h4>
          <div className="space-y-2">
            {audience_segments.slice(0, 3).map((segment: any, idx: number) => (
              <div key={idx} className="pl-4 border-l-2 border-gray-300 dark:border-gray-700">
                <p className="text-sm font-medium text-foreground">{segment.name}</p>
                <p className="text-xs text-muted-foreground">{segment.description}</p>
              </div>
            ))}
            {audience_segments.length > 3 && (
              <p className="text-xs text-muted-foreground">
                ... và {audience_segments.length - 3} segments khác
              </p>
            )}
          </div>
        </div>
      )}

      {/* Functional Requirements */}
      {functional_requirements && functional_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            📋 Functional Requirements ({functional_requirements.length}):
          </h4>
          <div className="space-y-2">
            {functional_requirements.slice(0, 5).map((req: any, idx: number) => (
              <div key={idx} className="pl-4 border-l-2 border-green-300 dark:border-green-700">
                <p className="text-sm font-medium text-foreground">
                  {req.name}{' '}
                  <span className="text-xs text-muted-foreground">({req.priority})</span>
                </p>
                <p className="text-xs text-muted-foreground">{req.description}</p>
              </div>
            ))}
            {functional_requirements.length > 5 && (
              <p className="text-xs text-muted-foreground">
                ... và {functional_requirements.length - 5} requirements khác
              </p>
            )}
          </div>
        </div>
      )}

      {/* Non-Functional Requirements Summary */}
      <div className="grid grid-cols-3 gap-2">
        {performance_requirements && performance_requirements.length > 0 && (
          <div className="text-xs">
            <strong>⚡ Performance:</strong> {performance_requirements.length}
          </div>
        )}
        {security_requirements && security_requirements.length > 0 && (
          <div className="text-xs">
            <strong>🔒 Security:</strong> {security_requirements.length}
          </div>
        )}
        {ux_requirements && ux_requirements.length > 0 && (
          <div className="text-xs">
            <strong>🎨 UX:</strong> {ux_requirements.length}
          </div>
        )}
      </div>

      {/* Scope */}
      {scope_capabilities && scope_capabilities.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            ⚙️ Capabilities ({scope_capabilities.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {scope_capabilities.slice(0, 3).map((cap: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">
                {cap}
              </li>
            ))}
            {scope_capabilities.length > 3 && (
              <li className="text-xs text-muted-foreground">
                ... và {scope_capabilities.length - 3} khác
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Dependencies, Risks, Assumptions Summary */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        {dependencies && dependencies.length > 0 && (
          <div>
            <strong>🔗 Dependencies:</strong> {dependencies.length}
          </div>
        )}
        {risks && risks.length > 0 && (
          <div>
            <strong>⚠️ Risks:</strong> {risks.length}
          </div>
        )}
        {assumptions && assumptions.length > 0 && (
          <div>
            <strong>💭 Assumptions:</strong> {assumptions.length}
          </div>
        )}
      </div>
    </div>
  )
}
