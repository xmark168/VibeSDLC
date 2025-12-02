---
name: unit-test
description: Write unit tests with Jest and React Testing Library. Use when testing components, utilities, server actions, or API routes. CRITICAL - Uses Jest (NOT Vitest).
---

# Unit Test (Jest + Testing Library)

⚠️ **CRITICAL: This project uses JEST, NOT Vitest!**

## NEVER USE (Will Cause Import Error):
- ❌ `import { vi } from 'vitest'`
- ❌ `vi.fn()`, `vi.mock()`, `vi.spyOn()`
- ❌ `import { describe, it, expect } from 'vitest'`

## ALWAYS USE:
- ✅ `jest.fn()`, `jest.mock()`, `jest.spyOn()`
- ✅ `jest.clearAllMocks()`
- ✅ No import for describe/it/expect (Jest globals)

---

## Critical Rules

1. **File**: `__tests__/*.test.ts` or `__tests__/*.test.tsx`
2. **Structure**: `describe` + `it` blocks with `beforeEach`
3. **Mocks**: Use `jest.fn()`, `jest.mock()` (NOT vitest)
4. **Queries**: Prefer `getByRole`, `getByLabelText`
5. **Async**: Always `await` userEvent and async ops
6. **Setup**: `jest.setup.ts` pre-mocks next/navigation, next/server

## ⚠️ Keep Tests Simple (KISS)

### What TO Test (Priority):
1. **Utilities** - Pure functions (formatDate, cn, validators)
2. **Components** - Render, click handlers, props
3. **Server Actions** - With mocked prisma (simple cases)

### What NOT to Test (SKIP):
- ❌ Complex API routes with multiple DB calls
- ❌ Full form submission flows
- ❌ Authentication flows
- ❌ File uploads
- ❌ Tests needing > 3 mocks

### Rule: If Hard to Test, Skip It
- Mock setup > 10 lines → **skip**
- Test needs real database → **skip**
- Test has > 3 async operations → **skip**

## Quick Reference

### Component Test
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

  it('can be disabled', () => {
    render(<Button disabled>Click</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Form Test
```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/LoginForm';

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('submits with valid data', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();

    render(<LoginForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });
});
```

### Utility Test
```typescript
import { cn, formatDate } from '@/lib/utils';

describe('cn', () => {
  it('merges classes', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditionals', () => {
    expect(cn('base', true && 'active')).toBe('base active');
  });
});
```

### Mock Patterns
```typescript
// Mock module (at top of file, outside describe)
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: jest.fn(),
      create: jest.fn(),
    },
  },
}));

// Mock fetch
global.fetch = jest.fn();

// Clear mocks in beforeEach
beforeEach(() => {
  jest.clearAllMocks();
});

// Mock implementation per test
(prisma.user.findUnique as jest.Mock).mockResolvedValue({ id: '1', name: 'Test' });
```

## Pre-configured Mocks (jest.setup.ts)

These are already mocked in `jest.setup.ts`:
- `next/navigation` (useRouter, usePathname, useSearchParams)
- `next/server` (NextResponse, NextRequest)
- `window.matchMedia`
- `IntersectionObserver`
- `ResizeObserver`

## Query Priority

| Priority | Query | Use Case |
|----------|-------|----------|
| 1 | `getByRole` | Buttons, links |
| 2 | `getByLabelText` | Form inputs |
| 3 | `getByText` | Static text |
| 4 | `getByTestId` | Last resort |

## Commands
```bash
bun test              # Run all tests
bun test --watch      # Watch mode
bun test --coverage   # With coverage
bun test path/to/file # Run specific file
```

## References

- `testing-patterns.md` - API routes, server actions, advanced mocks
- `common-issues.md` - Common errors and solutions
