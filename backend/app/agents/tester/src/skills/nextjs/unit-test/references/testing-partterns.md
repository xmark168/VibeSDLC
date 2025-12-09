# Advanced Testing Patterns (Jest)

## Testing with Mocks

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { UserProfile } from '@/components/UserProfile';

// Mock at module level
global.fetch = jest.fn();

describe('UserProfile', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays loading state', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<UserProfile userId="1" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays user after loading', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ name: 'John', email: 'john@example.com' }),
    });

    render(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByText('John')).toBeInTheDocument();
    });
  });

  it('displays error on failure', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
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

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: { create: jest.fn(), delete: jest.fn() },
  },
}));

jest.mock('next/cache', () => ({
  revalidatePath: jest.fn(),
}));

describe('User Actions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    it('creates user with valid data', async () => {
      (prisma.user.create as jest.Mock).mockResolvedValueOnce({ id: '1' });

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
      (prisma.user.delete as jest.Mock).mockResolvedValueOnce({});

      const result = await deleteUser('id');

      expect(result.success).toBe(true);
      expect(prisma.user.delete).toHaveBeenCalledWith({ where: { id: 'id' } });
    });
  });
});
```

## Testing API Routes

```typescript
import { GET, POST } from '@/app/api/users/route';
import { prisma } from '@/lib/prisma';

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findMany: jest.fn(),
      create: jest.fn(),
    },
  },
}));

describe('Users API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('GET /api/users', () => {
    it('returns users list', async () => {
      const mockUsers = [{ id: '1', name: 'John' }];
      (prisma.user.findMany as jest.Mock).mockResolvedValue(mockUsers);

      const request = new Request('http://localhost/api/users');
      const response = await GET(request);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.data).toEqual(mockUsers);
    });
  });

  describe('POST /api/users', () => {
    it('creates user', async () => {
      const mockUser = { id: '1', name: 'John', email: 'john@test.com' };
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const request = new Request('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({ name: 'John', email: 'john@test.com' }),
      });
      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.success).toBe(true);
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

## Type Casting for Mocks

```typescript
// Correct way to cast jest mocks
(prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
(fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

// For spies
const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
```