---
name: integration-test
description: Write integration tests with Jest for API routes and database operations. Use when testing backend logic, API endpoints, or data layer.
---

# Integration Test (Jest)

## ⛔ CRITICAL: NEVER CHECK response.status

**NextResponse.status is ALWAYS undefined in Jest environment.** This is a known limitation.

```typescript
// ⛔ WRONG - WILL ALWAYS FAIL (response.status is undefined)
const response = await GET(request);
expect(response.status).toBe(200);  // FAILS: Expected 200, Received: undefined

// ✅ CORRECT - Check data.success or data properties instead
const response = await GET(request);
const data = await response.json();
expect(data.success).toBe(true);     // Check API response structure
expect(data.data).toBeDefined();     // Check data exists
expect(data.error).toBeUndefined();  // No error for success

// ✅ For error cases - Check error response structure
const response = await POST(invalidRequest);
const data = await response.json();
expect(data.success).toBe(false);    // API returns success: false
expect(data.error).toBeDefined();    // Error message exists
```

**WHY:** When calling Next.js route handlers directly (not via HTTP), the Response object's `.status` property is not populated correctly in Jest's mock environment.

## ⚠️ CRITICAL RULES - READ FIRST
- **DO NOT** create config files (jest.config.*, tsconfig.json)
- Config files **ALREADY EXIST** in project - use them as-is
- **ONLY** create TEST files: *.test.ts
- **READ SOURCE CODE FIRST** - Check actual exports, types, function signatures before writing tests
- **DO NOT INVENT APIs** - Only test routes/functions that actually exist in the codebase
- **NEVER** use `response.status` - it's always undefined (see above)

## ⚠️ Response Methods in Jest
In Jest mock environment, use `response.json()` directly - do NOT use `response.text()`.

```typescript
// ❌ WRONG - response.text() is not available in Jest mock
const response = await GET(request);
const text = await response.text();  // ERROR: response.text is not a function

// ❌ WRONG - response.status is undefined
const response = await GET(request);
expect(response.status).toBe(200);   // FAILS: undefined !== 200

// ✅ CORRECT - Use response.json() and check data properties
const response = await GET(request);
const data = await response.json();
expect(data.success).toBe(true);     // Check success flag
expect(data.data).toEqual(expected); // Check actual data
```

**BEST PRACTICE:** For integration tests, mock at the database layer (Prisma) and check `data.success` or `data.error` instead of `response.status`.

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

## File Location (FIXED - DO NOT CHANGE)
```
src/__tests__/integration/     # Integration tests (Jest)
```
**IMPORTANT:** Always use `src/__tests__/integration/` for integration tests. Do NOT use other folders like `__tests__/integration/` or `tests/`.

## Test Structure

```typescript
import { POST } from '@/app/api/users/route';

// Mock functions at top level (outside describe)
const mockCreate = jest.fn();
const mockFindMany = jest.fn();
const mockFindUnique = jest.fn();

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      create: (...args: unknown[]) => mockCreate(...args),
      findMany: (...args: unknown[]) => mockFindMany(...args),
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
    },
  },
}));

describe('Story: {story_title}', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/users', () => {
    it('creates user with valid data', async () => {
      // Arrange
      const mockUser = { id: 'test-1', name: 'Test User', email: 'test@example.com' };
      mockCreate.mockResolvedValue(mockUser);
      
      // Act
      const request = new Request('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({ name: 'Test User', email: 'test@example.com' }),
      });
      const response = await POST(request);
      const data = await response.json();
      
      // Assert - Check data properties, NOT response.status
      expect(data.success).toBe(true);
      expect(data.data).toEqual(mockUser);
      expect(mockCreate).toHaveBeenCalledWith({
        data: { name: 'Test User', email: 'test@example.com' },
      });
    });

    it('returns error for invalid data', async () => {
      // Arrange - empty body
      const request = new Request('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      
      // Act
      const response = await POST(request);
      const data = await response.json();
      
      // Assert - Check error response, NOT response.status
      expect(data.success).toBe(false);
      expect(data.error).toBeDefined();
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
pnpm test                           # All tests
pnpm test tests/integration         # Integration only
pnpm test --coverage                # With coverage
pnpm test --watch                   # Watch mode
```

## Important Rules

1. **NO ESM packages** - Don't use uuid, nanoid. Use hardcoded IDs: `"test-id-123"`
2. **Clear mocks** - Always `jest.clearAllMocks()` in beforeEach
3. **Async/await** - Always await async operations
4. **Isolation** - Each test should be independent

## ❌ Anti-Patterns - DO NOT DO

### Don't create helper functions for response extraction
```typescript
// ❌ WRONG - Unnecessary abstraction, prone to errors
async function extractResponse(response: Response) {
  const data = await response.json();
  return { status: response.status, data };
}
const { status, data } = await extractResponse(response);

// ✅ CORRECT - Use directly, simple and clear
const response = await GET(request);
const data = await response.json();
expect(response.status).toBe(200);
```

### Don't check exact Prisma query structure
```typescript
// ❌ WRONG - Brittle, breaks on any refactor
expect(mockFindMany).toHaveBeenCalledWith({
  where: { OR: [{ title: { contains: 'test', mode: 'insensitive' } }] },
  skip: 0,
  take: 20,
  include: { category: { select: { id: true, name: true } } },
  orderBy: [{ featured: 'desc' }, { createdAt: 'desc' }],
});

// ✅ CORRECT - Check behavior via response data
expect(mockFindMany).toHaveBeenCalled();
expect(data).toHaveLength(2);
expect(data[0].title).toBe('Expected Title');
```

### Don't use Date objects in mock data
```typescript
// ❌ WRONG - Date comparison issues in assertions
const mockBook = {
  id: 'book-1',
  createdAt: new Date('2023-01-15'),
  updatedAt: new Date('2023-01-15'),
};

// ✅ CORRECT - Use ISO strings for dates
const mockBook = {
  id: 'book-1',
  createdAt: '2023-01-15T00:00:00.000Z',
  updatedAt: '2023-01-15T00:00:00.000Z',
};
```

### Keep mock data minimal
```typescript
// ❌ WRONG - Too many fields, hard to maintain
const mockUser = {
  id: 'user-1',
  name: 'Test User',
  email: 'test@example.com',
  phone: '123-456-7890',
  address: '123 Main St',
  city: 'Test City',
  country: 'Test Country',
  createdAt: '2023-01-01',
  updatedAt: '2023-01-01',
  role: 'user',
  isActive: true,
  // ... more fields
};

// ✅ CORRECT - Only include fields being tested
const mockUser = { id: 'user-1', name: 'Test User' };
```

## References
- `mock-patterns.md` - Advanced mocking patterns for Prisma, Auth, External APIs
