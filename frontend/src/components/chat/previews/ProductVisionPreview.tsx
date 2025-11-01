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
            {audience_segments.map((segment: any, idx: number) => (
              <div key={idx} className="pl-4 border-l-2 border-gray-300 dark:border-gray-700">
                <p className="text-sm font-medium text-foreground">{segment.name}</p>
                <p className="text-xs text-muted-foreground mb-1">{segment.description}</p>
                {segment.needs && segment.needs.length > 0 && (
                  <div className="mt-1">
                    <p className="text-xs font-medium text-foreground">Needs:</p>
                    <ul className="list-disc list-inside ml-2">
                      {segment.needs.map((need: string, nIdx: number) => (
                        <li key={nIdx} className="text-xs text-muted-foreground">{need}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {segment.pain_points && segment.pain_points.length > 0 && (
                  <div className="mt-1">
                    <p className="text-xs font-medium text-foreground">Pain Points:</p>
                    <ul className="list-disc list-inside ml-2">
                      {segment.pain_points.map((pain: string, pIdx: number) => (
                        <li key={pIdx} className="text-xs text-muted-foreground">{pain}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Functional Requirements */}
      {functional_requirements && functional_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            📋 Functional Requirements ({functional_requirements.length}):
          </h4>
          <div className="space-y-3">
            {functional_requirements.map((req: any, idx: number) => (
              <div key={idx} className="pl-4 border-l-2 border-green-300 dark:border-green-700">
                <p className="text-sm font-medium text-foreground">
                  {req.name}{' '}
                  <span className="text-xs text-muted-foreground">({req.priority})</span>
                </p>
                <p className="text-xs text-muted-foreground mb-1">{req.description}</p>
                {req.user_stories && req.user_stories.length > 0 && (
                  <div className="mt-1">
                    <p className="text-xs font-medium text-foreground">User Stories:</p>
                    <ul className="list-disc list-inside ml-2">
                      {req.user_stories.map((story: string, sIdx: number) => (
                        <li key={sIdx} className="text-xs text-muted-foreground">{story}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {req.acceptance_criteria && req.acceptance_criteria.length > 0 && (
                  <div className="mt-1">
                    <p className="text-xs font-medium text-foreground">Acceptance Criteria:</p>
                    <ul className="list-disc list-inside ml-2">
                      {req.acceptance_criteria.map((criteria: string, cIdx: number) => (
                        <li key={cIdx} className="text-xs text-muted-foreground">{criteria}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Non-Functional Requirements - Full Details */}
      {performance_requirements && performance_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            ⚡ Performance Requirements ({performance_requirements.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {performance_requirements.map((req: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{req}</li>
            ))}
          </ul>
        </div>
      )}

      {security_requirements && security_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            🔒 Security Requirements ({security_requirements.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {security_requirements.map((req: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{req}</li>
            ))}
          </ul>
        </div>
      )}

      {ux_requirements && ux_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            🎨 UX Requirements ({ux_requirements.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {ux_requirements.map((req: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{req}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Scope */}
      {scope_capabilities && scope_capabilities.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            ⚙️ Capabilities ({scope_capabilities.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {scope_capabilities.map((cap: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">
                {cap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {scope_non_goals && scope_non_goals.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            🚫 Non-Goals ({scope_non_goals.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {scope_non_goals.map((ng: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">
                {ng}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dependencies, Risks, Assumptions - Full Details */}
      {dependencies && dependencies.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            🔗 Dependencies ({dependencies.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {dependencies.map((dep: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{dep}</li>
            ))}
          </ul>
        </div>
      )}

      {risks && risks.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            ⚠️ Risks ({risks.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {risks.map((risk: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{risk}</li>
            ))}
          </ul>
        </div>
      )}

      {assumptions && assumptions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            💭 Assumptions ({assumptions.length}):
          </h4>
          <ul className="list-disc list-inside space-y-1">
            {assumptions.map((assumption: string, idx: number) => (
              <li key={idx} className="text-xs text-muted-foreground">{assumption}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
