---
name: integration-test
description: Write integration tests with Jest for API routes and database operations. Use when testing backend logic, API endpoints, or data layer.
---

# Integration Test (Jest)

## ⚠️ CRITICAL RULES - READ FIRST
- **DO NOT** create config files (jest.config.*, playwright.config.*, tsconfig.json)
- Config files **ALREADY EXIST** in project - use them as-is
- **ONLY** create TEST files: *.test.ts
- **READ SOURCE CODE FIRST** - Check actual exports, types, function signatures before writing tests
- **DO NOT INVENT APIs** - Only test routes/functions that actually exist in the codebase

## ⚠️ TYPESCRIPT STRICT RULES
```typescript
// ✅ CORRECT - Explicit types for ALL parameters
const mockFn = jest.fn((...args: unknown[]) => mockImpl(...args));
const handler = (req: Request, params: { id: string }) => {...};

// ❌ WRONG - Implicit any (will cause TS errors)
const mockFn = jest.fn((...args) => mockImpl(...args));  // Error: implicit any
const handler = (req, params) => {...};  // Error: implicit any
```

## ⚠️ IMPORT RULES
```typescript
// ✅ CORRECT imports
import { getServerSession } from 'next-auth';           // Named import
import { prisma } from '@/lib/prisma';                  // Named import
import { GET, POST } from '@/app/api/users/route';      // Named imports for route handlers

// ❌ WRONG imports - DO NOT USE
import getServerSession from 'next-auth';               // Wrong: not default export
import prisma from '@/lib/prisma';                      // Wrong: check actual export
```

## When to Use
- Testing API route handlers (GET, POST, PUT, DELETE)
- Testing database operations (Prisma)
- Testing service layer logic
- Testing with mocked external services

## File Location
Place tests in the integration folder detected by the system (e.g., `__tests__/integration/` or `src/__tests__/integration/`)

## Test Structure

```typescript
import { prismaMock } from '@/lib/__mocks__/prisma';

describe('Story: {story_title}', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/users', () => {
    it('creates user with valid data', async () => {
      // Arrange
      const mockUser = { id: 'test-1', name: 'Test User', email: 'test@example.com' };
      prismaMock.user.create.mockResolvedValue(mockUser);
      
      // Act
      const request = new Request('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({ name: 'Test User', email: 'test@example.com' }),
      });
      const response = await POST(request);
      
      // Assert
      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data).toEqual(mockUser);
      expect(prismaMock.user.create).toHaveBeenCalledWith({
        data: { name: 'Test User', email: 'test@example.com' },
      });
    });

    it('returns 400 for invalid data', async () => {
      // Arrange - empty body
      const request = new Request('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      
      // Act
      const response = await POST(request);
      
      // Assert
      expect(response.status).toBe(400);
    });
  });
});
```

## Mock Patterns

### Prisma Mock Setup
```typescript
// At top of file, outside describe
const mockFindUnique = jest.fn();
const mockCreate = jest.fn();
const mockUpdate = jest.fn();
const mockDelete = jest.fn();
const mockFindMany = jest.fn();

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
      create: (...args: unknown[]) => mockCreate(...args),
      update: (...args: unknown[]) => mockUpdate(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
      findMany: (...args: unknown[]) => mockFindMany(...args),
    },
  },
}));
```

### Fetch Mock
```typescript
global.fetch = jest.fn();

// In test
(fetch as jest.Mock).mockResolvedValue({
  ok: true,
  json: async () => ({ data: 'test' }),
});
```

### NextAuth Session Mock
```typescript
jest.mock('next-auth', () => ({
  getServerSession: jest.fn(),
}));

// In test
(getServerSession as jest.Mock).mockResolvedValue({
  user: { id: 'user-1', email: 'test@example.com' },
});
```

## AAA Pattern (Arrange-Act-Assert)

1. **Arrange**: Set up test data, mocks, preconditions
2. **Act**: Execute the code being tested
3. **Assert**: Verify expected outcomes

## Commands
```bash
bun run test                        # All tests
bun run test tests/integration      # Integration only
bun run test --coverage             # With coverage
bun run test --watch                # Watch mode
```

## Important Rules

1. **NO ESM packages** - Don't use uuid, nanoid. Use hardcoded IDs: `"test-id-123"`
2. **Clear mocks** - Always `jest.clearAllMocks()` in beforeEach
3. **Async/await** - Always await async operations
4. **Isolation** - Each test should be independent

## References
- `mock-patterns.md` - Advanced mocking patterns for Prisma, Auth, External APIs
