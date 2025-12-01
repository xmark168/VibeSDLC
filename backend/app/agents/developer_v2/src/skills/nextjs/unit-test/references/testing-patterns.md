# Advanced Testing Patterns

## Testing with Mocks

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { UserProfile } from '@/components/UserProfile';

global.fetch = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => '/users/1',
}));

describe('UserProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays loading state', () => {
    (fetch as any).mockImplementation(() => new Promise(() => {}));
    render(<UserProfile userId="1" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays user after loading', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ name: 'John', email: 'john@example.com' }),
    });

    render(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByText('John')).toBeInTheDocument();
    });
  });

  it('displays error on failure', async () => {
    (fetch as any).mockRejectedValueOnce(new Error('Network error'));
    render(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

## Testing Server Actions

```typescript
import { createUser, deleteUser } from '@/app/actions/user';
import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';

vi.mock('@/lib/prisma', () => ({
  prisma: {
    user: { create: vi.fn(), delete: vi.fn() },
  },
}));

vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

describe('User Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createUser', () => {
    it('creates user with valid data', async () => {
      (prisma.user.create as any).mockResolvedValueOnce({ id: '1' });

      const formData = new FormData();
      formData.append('name', 'John');
      formData.append('email', 'john@example.com');

      const result = await createUser(null, formData);

      expect(result.success).toBe(true);
      expect(revalidatePath).toHaveBeenCalledWith('/users');
    });

    it('returns validation errors', async () => {
      const formData = new FormData();
      formData.append('name', 'J');
      formData.append('email', 'invalid');

      const result = await createUser(null, formData);

      expect(result.success).toBe(false);
      expect(result.fieldErrors).toBeDefined();
    });
  });

  describe('deleteUser', () => {
    it('deletes successfully', async () => {
      (prisma.user.delete as any).mockResolvedValueOnce({});

      const result = await deleteUser('id');

      expect(result.success).toBe(true);
      expect(prisma.user.delete).toHaveBeenCalledWith({ where: { id: 'id' } });
    });
  });
});
```

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

## Async Patterns

```typescript
// Wait for element
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});

// Find (auto waits)
const element = await screen.findByText('Loaded');

// Wait for removal
await waitForElementToBeRemoved(() => screen.queryByText('Loading'));
```
