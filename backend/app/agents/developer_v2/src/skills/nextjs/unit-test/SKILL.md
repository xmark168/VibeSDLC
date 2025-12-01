---
name: unit-test
description: Write unit tests with Jest 30 and React Testing Library for Next.js 16 components and utilities
triggers:
  - test
  - jest
  - testing
  - spec
  - unit test
  - testing-library
  - describe
  - it
  - expect
version: "2.0"
author: VibeSDLC
---

# Unit Test Skill (Jest 30 + React Testing Library)

## Critical Rules

1. **File location** - `__tests__/` folder or co-locate with `*.test.tsx`
2. **Naming** - `ComponentName.test.tsx` or `utils.test.ts`
3. **Structure** - Use `describe` blocks with descriptive `it` statements
4. **User events** - Use `userEvent` over `fireEvent`
5. **Queries** - Prefer `getByRole`, `getByLabelText` over `getByTestId`
6. **Async** - Use `await` with `userEvent` and async operations
7. **Run tests** - `bun test` before committing

## Basic Component Test

```typescript
// components/__tests__/Button.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const user = userEvent.setup();
    const handleClick = jest.fn();

    render(<Button onClick={handleClick}>Click me</Button>);
    
    await user.click(screen.getByRole('button'));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
    render(<Button disabled>Click me</Button>);
    
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies variant styles', () => {
    render(<Button variant="destructive">Delete</Button>);
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-destructive');
  });
});
```

## Form Component Test

```typescript
// components/__tests__/LoginForm.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/LoginForm';

describe('LoginForm', () => {
  const user = userEvent.setup();

  it('renders all form fields', () => {
    render(<LoginForm onSubmit={jest.fn()} />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    render(<LoginForm onSubmit={jest.fn()} />);

    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });

  it('shows error for invalid email', async () => {
    render(<LoginForm onSubmit={jest.fn()} />);

    await user.type(screen.getByLabelText(/email/i), 'invalid-email');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
    });
  });

  it('calls onSubmit with form data when valid', async () => {
    const handleSubmit = jest.fn();
    render(<LoginForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('disables submit button while submitting', async () => {
    const handleSubmit = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
    render(<LoginForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /login/i }));

    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
```

## Utility Function Test

```typescript
// lib/__tests__/utils.test.ts
import { cn, formatDate, truncate } from '@/lib/utils';

describe('cn utility', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active', false && 'hidden')).toBe('base active');
  });

  it('handles Tailwind conflicts', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });

  it('handles undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
  });
});

describe('formatDate', () => {
  it('formats date correctly', () => {
    const date = new Date('2024-01-15');
    expect(formatDate(date)).toBe('January 15, 2024');
  });

  it('handles string input', () => {
    expect(formatDate('2024-01-15')).toBe('January 15, 2024');
  });
});

describe('truncate', () => {
  it('truncates long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
  });

  it('does not truncate short strings', () => {
    expect(truncate('Hi', 5)).toBe('Hi');
  });
});
```

## Testing with Mocks

```typescript
// components/__tests__/UserProfile.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { UserProfile } from '@/components/UserProfile';

// Mock fetch
global.fetch = jest.fn();

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/users/1',
}));

describe('UserProfile', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays loading state initially', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<UserProfile userId="1" />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays user data after loading', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: '1', name: 'John Doe', email: 'john@example.com' }),
    });

    render(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });
  });

  it('displays error message on fetch failure', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/error loading user/i)).toBeInTheDocument();
    });
  });
});
```

## Testing Server Actions

```typescript
// app/actions/__tests__/user.test.ts
import { createUser, deleteUser } from '@/app/actions/user';
import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';

// Mock prisma
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      create: jest.fn(),
      delete: jest.fn(),
    },
  },
}));

// Mock next/cache
jest.mock('next/cache', () => ({
  revalidatePath: jest.fn(),
}));

describe('User Actions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    it('creates user with valid data', async () => {
      const mockUser = { id: '1', name: 'John', email: 'john@example.com' };
      (prisma.user.create as jest.Mock).mockResolvedValueOnce(mockUser);

      const formData = new FormData();
      formData.append('name', 'John');
      formData.append('email', 'john@example.com');

      const result = await createUser(null, formData);

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: '1' });
      expect(revalidatePath).toHaveBeenCalledWith('/users');
    });

    it('returns validation errors for invalid data', async () => {
      const formData = new FormData();
      formData.append('name', 'J'); // Too short
      formData.append('email', 'invalid-email');

      const result = await createUser(null, formData);

      expect(result.success).toBe(false);
      expect(result.fieldErrors).toBeDefined();
      expect(result.fieldErrors?.name).toBeDefined();
      expect(result.fieldErrors?.email).toBeDefined();
    });
  });

  describe('deleteUser', () => {
    it('deletes user successfully', async () => {
      (prisma.user.delete as jest.Mock).mockResolvedValueOnce({});

      const result = await deleteUser('user-id');

      expect(result.success).toBe(true);
      expect(prisma.user.delete).toHaveBeenCalledWith({ where: { id: 'user-id' } });
      expect(revalidatePath).toHaveBeenCalledWith('/users');
    });

    it('returns error on failure', async () => {
      (prisma.user.delete as jest.Mock).mockRejectedValueOnce(new Error('Not found'));

      const result = await deleteUser('invalid-id');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Failed to delete user');
    });
  });
});
```

## Query Priority (Best to Worst)

| Priority | Query | Use Case |
|----------|-------|----------|
| 1 | `getByRole` | Buttons, links, headings |
| 2 | `getByLabelText` | Form inputs |
| 3 | `getByPlaceholderText` | Inputs without labels |
| 4 | `getByText` | Non-interactive elements |
| 5 | `getByDisplayValue` | Current input value |
| 6 | `getByAltText` | Images |
| 7 | `getByTitle` | Elements with title |
| 8 | `getByTestId` | Last resort |

## Common Assertions

```typescript
// Presence
expect(element).toBeInTheDocument();
expect(element).not.toBeInTheDocument();

// State
expect(element).toBeDisabled();
expect(element).toBeEnabled();
expect(element).toBeVisible();
expect(element).toHaveValue('text');

// Classes/Attributes
expect(element).toHaveClass('active');
expect(element).toHaveAttribute('href', '/home');

// Text content
expect(element).toHaveTextContent('Hello');

// Mock calls
expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledTimes(1);
expect(mockFn).toHaveBeenCalledWith(arg1, arg2);
```

## Run Tests

```bash
# Run all tests
bun test

# Run tests in watch mode
bun test:watch

# Run tests with coverage
bun test:coverage

# Run specific file
bun test Button.test.tsx
```
