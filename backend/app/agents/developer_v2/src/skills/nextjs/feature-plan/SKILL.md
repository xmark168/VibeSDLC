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
