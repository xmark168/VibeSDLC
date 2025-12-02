---
name: feature-plan
description: Create implementation plans for Next.js features. Use when breaking down user stories into tasks, planning feature implementation, or decomposing complex requirements.
---

# Feature Plan

## Critical Rules

1. **Vertical slicing** - Each task delivers complete functionality across layers
2. **INVEST** - Independent, Negotiable, Valuable, Estimable, Small, Testable
3. **Order**: Data → Logic → UI → Tests

## Quick Reference

### Task Decomposition Patterns

| Pattern | Example |
|---------|---------|
| Workflow | Login → Dashboard → Search → Details |
| CRUD | Create, Read, Update, Delete |
| Scenarios | Happy path, Edge cases, Errors |

### Completeness Checklist

| Layer | Questions |
|-------|-----------|
| Data | Schema changes? Migration? |
| Logic | API route or Server Action? Validation? |
| UI | New components? Where displayed? |
| States | Loading? Error? Empty? |
| Tests | Unit tests (Jest)? |

### Task Order
```
1. Data/Schema
2. Core logic (API/Action)
3. UI components
4. Wire to pages
5. Error handling
6. Tests
```

## Common Gaps

- Error handling and user feedback
- Loading states
- Empty states
- Input validation (client + server)
- Connecting to existing pages/layouts
- Unit tests (Jest only, no e2e)

## ⚠️ CRITICAL: Test Guidelines

### ONLY Unit Tests (Jest)
- ✅ Test individual functions in isolation
- ✅ Mock ALL external dependencies (prisma, fetch)
- ✅ Simple assertions, no complex setup
- ✅ Max 2-3 test tasks per feature

### NEVER Write:
- ❌ Integration tests (multiple components together)
- ❌ E2E tests (Playwright, Cypress)
- ❌ Tests requiring real database connection
- ❌ Tests with complex async flows (> 3 awaits)

### Good Test Tasks:
- "Create unit tests for formatCurrency utility"
- "Create unit tests for Button component"

### Bad Test Tasks (SKIP):
- "Create integration tests for checkout flow"
- "Create tests for API with real database"

## Available Libraries

| Purpose | Library | Usage |
|---------|---------|-------|
| Animations | `framer-motion` | Page transitions, hover effects, list animations |
| Forms | `react-hook-form` + `zod` | Form validation and state |
| State | `zustand` | Global state management |
| UI | `shadcn/ui` | Component library |
| Icons | `lucide-react` | Icon set |
| Charts | `recharts` | Data visualization |
| Toast | `sonner` | Notifications |

## Output Format

**CRITICAL**: Always respond with JSON wrapped in result tags:

```
<result>
{
  "story_summary": "Brief feature summary (1 sentence)",
  "steps": [
    {
      "order": 1,
      "description": "What to do (not how)",
      "file_path": "exact/file/path.tsx",
      "action": "create|modify|delete|test|config"
    }
  ]
}
</result>
```

### Action Types
- **create**: New files (components, pages, APIs)
- **modify**: Update existing files (schema, pages)
- **delete**: Remove files (rare)
- **test**: Test files (Jest unit tests)
- **config**: Configuration files

### Path Guidelines
- Use exact paths from project_structure
- Components: `src/components/[Feature]/ComponentName.tsx`
- Pages: `src/app/[route]/page.tsx`
- APIs: `src/app/api/[resource]/route.ts`
- Actions: `src/app/actions/[domain].ts`
