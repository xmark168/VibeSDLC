# Mock Patterns for Integration Tests

## Prisma Client Mock

### Basic Setup
```typescript
const mockFindUnique = jest.fn();
const mockCreate = jest.fn();
const mockUpdate = jest.fn();
const mockDelete = jest.fn();
const mockFindMany = jest.fn();
const mockFindFirst = jest.fn();

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
      findFirst: (...args: unknown[]) => mockFindFirst(...args),
      findMany: (...args: unknown[]) => mockFindMany(...args),
      create: (...args: unknown[]) => mockCreate(...args),
      update: (...args: unknown[]) => mockUpdate(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
    },
    // Add other models as needed
    post: {
      findMany: jest.fn(),
      create: jest.fn(),
    },
  },
}));
```

### Transaction Mock
```typescript
const mockTransaction = jest.fn();

jest.mock('@/lib/prisma', () => ({
  prisma: {
    $transaction: (...args: unknown[]) => mockTransaction(...args),
    user: { ... },
  },
}));

// Usage
mockTransaction.mockImplementation(async (callback) => {
  return callback({ user: { create: mockCreate } });
});
```

## NextAuth Mock

### getServerSession
```typescript
import { getServerSession } from 'next-auth';

jest.mock('next-auth', () => ({
  getServerSession: jest.fn(),
}));

// Authenticated user
(getServerSession as jest.Mock).mockResolvedValue({
  user: { 
    id: 'user-123', 
    email: 'test@example.com',
    name: 'Test User',
  },
  expires: '2024-12-31',
});

// Unauthenticated
(getServerSession as jest.Mock).mockResolvedValue(null);
```

### auth() (Auth.js v5)
```typescript
jest.mock('@/auth', () => ({
  auth: jest.fn(),
}));

(auth as jest.Mock).mockResolvedValue({
  user: { id: 'user-123' },
});
```

## External API Mock

### Fetch
```typescript
global.fetch = jest.fn();

// Success response
(fetch as jest.Mock).mockResolvedValue({
  ok: true,
  status: 200,
  json: async () => ({ data: 'success' }),
});

// Error response
(fetch as jest.Mock).mockResolvedValue({
  ok: false,
  status: 404,
  json: async () => ({ error: 'Not found' }),
});

// Network error
(fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
```

### Axios
```typescript
jest.mock('axios');
import axios from 'axios';

(axios.get as jest.Mock).mockResolvedValue({ data: { result: 'test' } });
(axios.post as jest.Mock).mockResolvedValue({ data: { id: 'new-123' } });
```

## File Upload Mock

```typescript
// Mock FormData
const mockFile = new File(['content'], 'test.txt', { type: 'text/plain' });
const formData = new FormData();
formData.append('file', mockFile);

const request = new Request('http://localhost/api/upload', {
  method: 'POST',
  body: formData,
});
```

## Environment Variables Mock

```typescript
// Save original
const originalEnv = process.env;

beforeEach(() => {
  process.env = { ...originalEnv, API_KEY: 'test-key' };
});

afterEach(() => {
  process.env = originalEnv;
});
```

## Date/Time Mock

```typescript
beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2024-01-15T10:00:00Z'));
});

afterEach(() => {
  jest.useRealTimers();
});
```

## bcrypt Mock (for password hashing)

```typescript
jest.mock('bcryptjs', () => ({
  hash: jest.fn().mockResolvedValue('hashed-password'),
  compare: jest.fn().mockResolvedValue(true),
}));
```

## Cookies Mock

```typescript
jest.mock('next/headers', () => ({
  cookies: jest.fn(() => ({
    get: jest.fn().mockReturnValue({ value: 'session-token' }),
    set: jest.fn(),
    delete: jest.fn(),
  })),
}));
```

## Tips

1. **Reset mocks**: Always `jest.clearAllMocks()` in `beforeEach`
2. **Type safety**: Use `as jest.Mock` for TypeScript
3. **Isolation**: Each test should set up its own mock responses
4. **Verify calls**: Use `toHaveBeenCalledWith()` to verify correct arguments
