/**
 * Preview Components for Agent Outputs
 *
 * Each agent type has its own preview component for rendering its output.
 * To add a new agent preview:
 * 1. Create a new component file (e.g., BacklogPreview.tsx)
 * 2. Export it here
 * 3. Add routing logic in agent-preview-modal.tsx
 */

export { ProductBriefPreview } from './ProductBriefPreview'
export { ProductVisionPreview } from './ProductVisionPreview'

// Future agent previews:
// export { BacklogPreview } from './BacklogPreview'
// export { SprintPlanPreview } from './SprintPlanPreview'
