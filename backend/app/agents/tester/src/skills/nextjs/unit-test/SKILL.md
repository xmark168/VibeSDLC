---
name: unit-test
description: Write unit tests with Jest and React Testing Library. Use when testing components, utilities, server actions, or API routes. CRITICAL - Uses Jest (NOT Vitest).
---

# Unit Test (Jest + Testing Library)

⚠️ **CRITICAL: This project uses JEST, NOT Vitest!**

## ⛔ CRITICAL: ONLY IMPORT FILES THAT EXIST!

**Before importing ANY component/file, CHECK the pre-loaded source code!**

```typescript
// ⛔ WRONG - Importing non-existent component
import { EducationLevelCategories } from '@/components/categories/EducationLevelCategories';
// ERROR: Cannot find module

// ✅ CORRECT - Import component that EXISTS in source code
import { CategoryCard } from '@/components/categories/CategoryCard';
// This file was shown in pre-loaded dependencies
```

**If no specific component exists for the story:**
1. Test a RELATED component that EXISTS (CategoryCard, BookCard, SearchBar, etc.)
2. Test the component's props, rendering, and basic interactions
3. DO NOT invent/create new components

## NEVER USE (Will Cause Import Error):
- ❌ `import { vi } from 'vitest'`
- ❌ `vi.fn()`, `vi.mock()`, `vi.spyOn()`
- ❌ `import { describe, it, expect } from 'vitest'`
- ❌ Import components that don't exist in source code

## ALWAYS USE:
- ✅ `jest.fn()`, `jest.mock()`, `jest.spyOn()`
- ✅ `jest.clearAllMocks()`
- ✅ No import for describe/it/expect (Jest globals)
- ✅ Only import files shown in pre-loaded dependencies

---

## Critical Rules

1. **File**: `__tests__/*.test.ts` or `__tests__/*.test.tsx`
2. **Structure**: `describe` + `it` blocks with `beforeEach`
3. **Mocks**: Use `jest.fn()`, `jest.mock()` (NOT vitest)
4. **Queries**: Prefer `getByRole`, `getByLabelText`
5. **Async**: Always `await` userEvent and async ops
6. **Setup**: `jest.setup.ts` pre-mocks next/navigation, next/server

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

## ⚠️ CRITICAL: Read Source Code Before Writing Selectors

**NEVER assume CSS classes or data attributes - CHECK THE SOURCE CODE!**

### Wrong Selector Patterns
```typescript
// ⛔ WRONG - Assuming class names exist
container.querySelector('[class*="badge"]');  // Component may not have "badge" class!

// ⛔ WRONG - Assuming data-testid exists
screen.getAllByTestId('skeleton');  // Component uses data-slot='skeleton', not data-testid!

// ⛔ WRONG - Assuming specific filenames
expect(img).toHaveAttribute('src', 'elementary-books.jpg');  // Hardcoded filename!

// ⛔ WRONG - Using CSS class selectors
container.querySelector('.card-title');  // Class may not exist or be different!
```

### Correct Selector Patterns
```typescript
// ✅ CORRECT - Use semantic queries from Testing Library
screen.getByRole('button', { name: /submit/i });
screen.getByRole('heading', { name: /categories/i });
screen.getByRole('link', { name: /view all/i });

// ✅ CORRECT - Query by actual text content from props
expect(screen.getByText(category.name)).toBeInTheDocument();
expect(screen.getByText(book.title)).toBeInTheDocument();

// ✅ CORRECT - Flexible image check (don't assume filename)
const img = screen.getByRole('img');
expect(img).toHaveAttribute('src');  // Just check src exists
expect(img.getAttribute('src')).toBeTruthy();

// ✅ CORRECT - Query by role with accessible name
screen.getByRole('img', { name: category.name });  // Uses alt text

// ✅ CORRECT - For loading states, check visual feedback
expect(screen.getByText(/loading/i)).toBeInTheDocument();
// OR check element count changes
expect(container.children.length).toBeGreaterThan(0);
```

### Testing Component Props (from pre-loaded source)
```typescript
// Look at the component source to understand its props:
// CategoryCard.tsx: interface Props { category: Category; onClick?: () => void }

// ✅ Test with actual props structure
render(<CategoryCard category={{ id: '1', name: 'Math', imageUrl: '/math.jpg' }} />);

// ⛔ Don't invent props that don't exist
render(<CategoryCard title="Math" badge="5 books" />);  // WRONG - these props don't exist!
```

## Commands
```bash
pnpm test              # Run all tests
pnpm test --watch      # Watch mode
pnpm test --coverage   # With coverage
pnpm test path/to/file # Run specific file
```

## ❌ Anti-Patterns - DO NOT DO

### Don't import non-existent components
```typescript
// ❌ WRONG - Component doesn't exist in codebase
import { EducationLevelFilter } from '@/components/EducationLevelFilter';
import { GradeBrowser } from '@/components/GradeBrowser';

// ✅ CORRECT - Use components that EXIST in pre-loaded source
import { CategoryCard } from '@/components/categories/CategoryCard';
import { BookCard } from '@/components/books/BookCard';
```

### Don't mock fetch if component doesn't use it
```typescript
// ❌ WRONG - Testing fetch when component doesn't call fetch
global.fetch = jest.fn();
render(<CategoryCard category={mockCategory} />);
expect(fetch).toHaveBeenCalled(); // FAILS - CategoryCard doesn't call fetch!

// ✅ CORRECT - Test what the component actually does
render(<CategoryCard category={mockCategory} />);
expect(screen.getByText(mockCategory.name)).toBeInTheDocument();
```

### Don't test implementation details
```typescript
// ❌ WRONG - Testing internal state/implementation
expect(component.state.isLoading).toBe(false);
expect(component.instance().handleClick).toBeDefined();

// ✅ CORRECT - Test user-visible behavior
expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
expect(screen.getByRole('button')).toBeEnabled();
```

### Don't invent props that don't exist
```typescript
// ❌ WRONG - Props don't exist on this component
render(<CategoryCard onLevelSelect={jest.fn()} gradeLevel="high" />);

// ✅ CORRECT - Check component's actual props in source code
render(<CategoryCard category={mockCategory} />);
```

### Test existing behavior, not imagined features
```typescript
// ❌ WRONG - Testing features that don't exist
it('filters by education level', async () => { /* ... */ });
it('calls API when level changes', async () => { /* ... */ });

// ✅ CORRECT - Test what the component ACTUALLY does
it('renders category name', () => {
  render(<CategoryCard category={{ id: '1', name: 'Math' }} />);
  expect(screen.getByText('Math')).toBeInTheDocument();
});

it('renders book count', () => {
  render(<CategoryCard category={{ id: '1', name: 'Math', bookCount: 5 }} />);
  expect(screen.getByText('5')).toBeInTheDocument();
});
```

## References

- `testing-patterns.md` - API routes, server actions, advanced mocks
- `common-issues.md` - Common errors and solutions