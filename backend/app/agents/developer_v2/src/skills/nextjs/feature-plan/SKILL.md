---
name: feature-plan
description: Create implementation plans for Next.js features. Use when breaking down user stories into tasks, planning feature implementation, or decomposing complex requirements.
---

This skill guides creation of implementation plans that break features into actionable tasks.

The user provides a feature request or user story that needs to be decomposed into concrete implementation steps.

## Planning Approach

Use vertical slicing to deliver complete functionality in each task:
- **Vertical slice**: Each task includes data, logic, and UI for one user-visible capability
- **INVEST criteria**: Independent, Negotiable, Valuable, Estimable, Small, Testable
- **Order**: Data - Logic - UI - Tests

**CRITICAL**: Avoid horizontal slicing (all models, then all APIs, then all UI). Instead, implement one complete feature at a time.

## Vertical Slice Example

**Feature**: Add to Cart

Bad approach (horizontal slicing):
1. Create all database models
2. Create all API routes
3. Create all components
4. Connect everything

Good approach (vertical slicing):
1. **Add single item to cart**
   - Schema: Cart, CartItem models
   - API: POST /api/cart/items
   - UI: "Add to Cart" button
   - Test: Button adds item

2. **View cart contents**
   - API: GET /api/cart
   - UI: Cart page with items list
   - Test: Cart displays items

3. **Update item quantity**
   - API: PUT /api/cart/items/[id]
   - UI: Quantity +/- buttons
   - Test: Quantity updates

## Task Structure

For each task, specify:
- **order**: Sequence number
- **description**: What to accomplish (not how)
- **file_path**: Exact file to create or modify
- **action**: create, modify, delete, test, or config

## Completeness Checklist

Ensure each feature covers:
- **Data layer**: Schema changes, migrations
- **Logic layer**: API route or Server Action with validation
- **UI layer**: Components, pages, where they're displayed
- **States**: Loading, error, empty states
- **Tests**: Unit tests (Jest only)

## Test Guidelines

**CRITICAL**: Only write unit tests. Never write integration or E2E tests.

Write tests for:
- Utility functions (formatDate, validators)
- Simple component rendering
- Server Actions with mocked Prisma

Skip tests for:
- Complex API routes
- Full form flows
- Authentication flows
- Anything needing more than 3 mocks

## Common Gaps

Features often miss:
- Error handling and user feedback
- Loading states during async operations
- Empty states when no data
- Input validation (client + server)
- Connecting new UI to existing pages/layouts

## Available Libraries

Use these pre-installed libraries:
- **framer-motion**: Page transitions, hover effects, list animations
- **react-hook-form + zod**: Form validation and state
- **zustand**: Global state management
- **shadcn/ui**: Component library
- **lucide-react**: Icon set
- **recharts**: Data visualization
- **sonner**: Toast notifications

## Output Format

Always respond with JSON wrapped in result tags:

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

NEVER:
- Use horizontal slicing (all of one layer before the next)
- Create more than 2-3 test tasks per feature
- Write integration or E2E tests
- Forget loading/error/empty states

**IMPORTANT**: Each task should result in visible, testable progress. A user should be able to see something working after each task.
