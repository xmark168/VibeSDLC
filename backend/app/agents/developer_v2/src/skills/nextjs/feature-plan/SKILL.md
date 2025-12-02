---
name: feature-plan
description: Create complete implementation plans for Next.js features. Use when breaking down user stories into tasks.
internal: true
---

# Feature Plan

## Core Principles

### 1. Vertical Slicing
Each task should deliver **complete, testable functionality** across all layers:
- ✅ Good: "Create search API with validation and error handling"
- ❌ Bad: "Create backend", "Create frontend" (horizontal slicing)

### 2. INVEST Criteria
Each task should be:
- **I**ndependent - Can be developed/tested alone
- **N**egotiable - Flexible on implementation details
- **V**aluable - Delivers user or business value
- **E**stimable - Clear enough to estimate effort
- **S**mall - Completable in reasonable time
- **T**estable - Has clear success criteria

## Task Decomposition Patterns

Use these patterns to split complex stories:

### By Workflow Steps
Split along user journey steps:
```
Login → Dashboard → Search → View Details → Checkout
```

### By Business Rules
Split by different conditions/rules:
```
- Free shipping for orders > $50
- Standard shipping calculation
- Express shipping option
```

### By Data Operations (CRUD)
```
- Create new item
- Read/List items  
- Update item
- Delete item
```

### By User Scenarios
```
- Happy path (success case)
- Edge cases (empty, max limit)
- Error cases (invalid input, not found)
```

### By Interface/Entry Points
```
- Web UI implementation
- API endpoint
- CLI command
```

## Completeness Checklist

Before finalizing, verify plan covers (if applicable):

| Layer | Questions |
|-------|-----------|
| **Data** | Schema changes needed? Migration required? |
| **Logic** | API route or Server Action? Validation? |
| **UI** | New components? Where do they appear? |
| **States** | Loading? Error? Empty? Success feedback? |
| **Tests** | Unit tests for components/utils? API route tests? (Jest, NOT e2e) |

## Common Gaps

⚠️ Plans often miss:
- Error handling and user feedback (toast/alert)
- Loading states during async operations
- Empty states when no data
- Input validation (client + server)
- Connecting new components to existing pages/layouts
- Database indexes for query performance
- Unit tests (Jest - NOT e2e tests, boilerplate only has Jest)

## Task Ordering

Recommended sequence:
```
1. Data/Schema (if needed)
2. Core logic (API/Action)
3. UI components
4. Wire up to pages/layouts
5. Edge cases & error handling
6. Tests
```

**Note**: Not all features need all layers. A refactor may only touch logic. A UI change may not need API work. Adapt based on the story.
