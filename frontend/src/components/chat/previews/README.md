# Agent Preview Components

This folder contains specialized preview components for each agent type in the system.

## Architecture

```
previews/
├── index.ts                      # Central export point
├── ProductBriefPreview.tsx       # Gatherer Agent output
├── ProductVisionPreview.tsx      # Vision Agent output
└── README.md                     # This file
```

## Current Components

### 1. ProductBriefPreview
**Agent:** Gatherer Agent
**Preview Type:** `product_brief`
**Data Structure:**
```typescript
{
  product_name: string
  description: string
  target_audience: string[]
  key_features: string[]
  benefits: string[]
  competitors: string[]
  completeness_note?: string
}
```

### 2. ProductVisionPreview
**Agent:** Vision Agent
**Preview Type:** `product_vision`
**Data Structure:**
```typescript
{
  draft_vision_statement: string
  experience_principles: string[]
  problem_summary: string
  audience_segments: Array<{name, description, needs, pain_points}>
  functional_requirements: Array<{name, description, priority, user_stories, acceptance_criteria}>
  performance_requirements: string[]
  security_requirements: string[]
  ux_requirements: string[]
  scope_capabilities: string[]
  scope_non_goals: string[]
  dependencies: string[]
  risks: string[]
  assumptions: string[]
}
```

## Adding a New Agent Preview

### Step 1: Create Component File

Create a new file (e.g., `BacklogPreview.tsx`):

```tsx
interface BacklogPreviewProps {
  backlog: any
  // Add other props specific to this preview
}

export function BacklogPreview({ backlog }: BacklogPreviewProps) {
  if (!backlog) return null

  // Render your preview here
  return (
    <div className="space-y-4 max-h-[500px] overflow-y-auto">
      {/* Your preview UI */}
    </div>
  )
}
```

### Step 2: Export in index.ts

```typescript
export { BacklogPreview } from './BacklogPreview'
```

### Step 3: Add Routing in agent-preview-modal.tsx

```typescript
const renderContent = () => {
  switch (preview.preview_type) {
    case 'product_brief':
      return <ProductBriefPreview ... />
    case 'product_vision':
      return <ProductVisionPreview ... />
    case 'backlog':  // Add new case
      return <BacklogPreview backlog={preview.backlog} />
    default:
      // Fallback logic
  }
}
```

### Step 4: Update Type in useChatWebSocket.ts

```typescript
export type AgentPreview = {
  preview_id: string
  agent: string
  preview_type: string
  title: string
  brief?: any
  vision?: any
  backlog?: any  // Add new field
  // ... other fields
}
```

### Step 5: Update Backend Agent

Make sure your backend agent sends the correct preview message:

```python
preview_message = {
    "type": "agent_preview",
    "preview_id": str(uuid.uuid4()),
    "agent": "Backlog Agent",
    "preview_type": "backlog",
    "title": "📋 PREVIEW - Product Backlog",
    "backlog": {...},  # Your backlog data
    "options": ["approve", "edit"],
    "prompt": "Bạn muốn làm gì với Backlog này?"
}
```

## Design Guidelines

1. **Consistent Layout**: Use same spacing classes (`space-y-4`, `max-h-[500px]`, etc.)
2. **Responsive**: Components should work on mobile and desktop
3. **Overflow Handling**: Use `overflow-y-auto` for long content
4. **Empty State**: Always check if data exists before rendering
5. **Typography**:
   - Section headers: `text-sm font-semibold text-foreground mb-1`
   - Content: `text-sm text-muted-foreground`
6. **Icons**: Use emojis or lucide-react icons for visual hierarchy
7. **Color Coding**: Use border colors to differentiate sections (e.g., `border-l-2 border-green-300`)

## Future Agents

Planned preview components:
- [ ] BacklogPreview - For Backlog Agent output
- [ ] SprintPlanPreview - For Priority/Sprint Planning Agent output

## Testing

When adding a new preview component:
1. Test with complete data
2. Test with missing/partial data
3. Test with empty data
4. Test on mobile viewport
5. Test in dark mode
