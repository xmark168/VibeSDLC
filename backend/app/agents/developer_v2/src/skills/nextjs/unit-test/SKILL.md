---
name: unit-test
description: Write unit tests with Vitest and React Testing Library. Use when creating tests for components, utilities, or server actions.
---

# Unit Test (Vitest + Testing Library)

## Critical Rules

1. **File**: `*.test.tsx` or `__tests__/*.test.tsx`
2. **Structure**: `describe` + `it` blocks
3. **User events**: Use `userEvent` over `fireEvent`
4. **Queries**: Prefer `getByRole`, `getByLabelText`
5. **Async**: Always `await` userEvent and async ops
6. **Run**: `bun test` before committing

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
    const onClick = vi.fn();

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
  it('submits with valid data', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

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
// Mock fetch
global.fetch = vi.fn();

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  prisma: { user: { create: vi.fn(), delete: vi.fn() } },
}));
```

## Query Priority

| Priority | Query | Use Case |
|----------|-------|----------|
| 1 | `getByRole` | Buttons, links |
| 2 | `getByLabelText` | Form inputs |
| 3 | `getByText` | Static text |
| 4 | `getByTestId` | Last resort |

## Commands
```bash
bun test           # Run tests
bun test:watch     # Watch mode
bun test:coverage  # With coverage
```

## References

- `testing-patterns.md` - Mocks, async, server actions
