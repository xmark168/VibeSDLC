---
name: unit-test
description: Write unit tests with Jest and React Testing Library. Use when testing components, utilities, server actions, or API routes. CRITICAL - Uses Jest (NOT Vitest).
---

This skill guides creation of unit tests using Jest and React Testing Library.

The user needs to test components, utility functions, or server-side logic with proper mocking and assertions.

## Before You Start

**CRITICAL**: This project uses Jest, NOT Vitest. Using Vitest imports will cause errors.

NEVER use:
- `import { vi } from 'vitest'`
- `vi.fn()`, `vi.mock()`, `vi.spyOn()`

ALWAYS use:
- `jest.fn()`, `jest.mock()`, `jest.spyOn()`
- `jest.clearAllMocks()` in `beforeEach`
- No imports for `describe`/`it`/`expect` (Jest globals)

## Keep Tests Simple

Focus on testing what matters. Skip complex tests that are hard to maintain.

**What TO Test:**
- **Utilities**: Pure functions like formatDate, validators, helpers
- **Components**: Rendering, click handlers, prop changes
- **Server Actions**: With mocked Prisma (simple cases only)

**What NOT to Test (skip these):**
- Complex API routes with multiple database calls
- Full form submission flows
- Authentication flows
- Tests needing more than 3 mocks

**Rule of Thumb**: If mock setup exceeds 10 lines, skip the test.

## Test File Structure

```typescript
// __tests__/feature.test.ts
describe('FeatureName', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockData = { id: '1', name: 'Test' };

  describe('happy path', () => {
    it('should do X when Y', async () => {
      // Arrange, Act, Assert
    });
  });

  describe('edge cases', () => {
    it('should handle empty input', async () => { });
    it('should handle unicode characters', async () => { });
  });

  describe('error handling', () => {
    it('should throw on database error', async () => { });
  });
});
```

## Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('handles click', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();

    render(<Button onClick={onClick}>Click</Button>);
    await user.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

## Mocking Modules

```typescript
// At top of file, outside describe
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: jest.fn(),
      create: jest.fn(),
    },
  },
}));

// In test
import { prisma } from '@/lib/prisma';

it('should find user', async () => {
  (prisma.user.findUnique as jest.Mock).mockResolvedValue({ id: '1', name: 'Test' });
  
  const result = await findUser('1');
  
  expect(result).toEqual({ id: '1', name: 'Test' });
});
```

## Query Priority

Use the most accessible query:
- **getByRole**: Buttons, links, form elements
- **getByLabelText**: Form inputs with labels
- **getByText**: Static text content
- **getByTestId**: Last resort only

## Pre-configured Mocks

These are already mocked in `jest.setup.ts`:
- `next/navigation` (useRouter, usePathname, useSearchParams)
- `next/server` (NextResponse, NextRequest)
- `window.matchMedia`, `IntersectionObserver`, `ResizeObserver`

## Commands

```bash
bun test              # Run all tests
bun test --watch      # Watch mode
bun test --coverage   # With coverage report
bun test path/to/file # Run specific file
```

NEVER:
- Import from vitest (causes immediate error)
- Skip `beforeEach` with `jest.clearAllMocks()`
- Use `getByTestId` as first choice
- Write tests requiring real database

**IMPORTANT**: Always `await` userEvent actions and use `waitFor` for async state updates.
