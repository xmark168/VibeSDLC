---
name: api-route
description: Create Next.js 16 API Route Handlers. Use when building REST endpoints (GET, POST, PUT, DELETE), implementing CRUD operations, or creating authenticated APIs with Zod validation.
---

# API Route Handler (Next.js 16)

## Critical Rules

1. **File**: `route.ts` in `app/api/` directory
2. **Exports**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
3. **Async params**: MUST `await params` in dynamic routes
4. **Zod validation**: Always validate request body
5. **Error handling**: Use `handleError()` - catches Zod, ApiException, and generic errors

## Quick Reference

### Collection Route
```typescript
// app/api/users/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';
import { successResponse, handleError, ApiErrors, HttpStatus } from '@/lib/api-response';
import { auth } from '@/auth';

const createSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function GET(request: NextRequest) {
  try {
    const users = await prisma.user.findMany();
    return successResponse(users);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await auth();
    if (!session) throw ApiErrors.unauthorized();

    const body = await request.json();
    const validated = createSchema.safeParse(body);
    if (!validated.success) return handleError(validated.error);

    const user = await prisma.user.create({ data: validated.data });
    return successResponse(user, 'Created', HttpStatus.CREATED);
  } catch (error) {
    return handleError(error);
  }
}
```

### Dynamic Route (MUST await params)
```typescript
// app/api/users/[id]/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;  // MUST await
    
    const user = await prisma.user.findUnique({ where: { id } });
    if (!user) throw ApiErrors.notFound('User');
    
    return successResponse(user);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    await prisma.user.delete({ where: { id } });
    return successResponse({ message: 'Deleted' });
  } catch (error) {
    return handleError(error);
  }
}
```

## Error Handling

```typescript
// handleError() catches all:
// - ZodError - 422 with formatted field errors
// - ApiException - Custom status with error code
// - Generic Error - 500 with message

// Predefined errors:
throw ApiErrors.unauthorized();      // 401
throw ApiErrors.forbidden();         // 403
throw ApiErrors.notFound('User');    // 404
throw ApiErrors.badRequest('msg');   // 400
throw ApiErrors.conflict('msg');     // 409
throw ApiErrors.validation('msg');   // 422
```

## Common Patterns

| Pattern | Code |
|---------|------|
| Pagination | `skip: (page-1)*limit, take: limit` |
| Search | `where: { field: { contains: q, mode: 'insensitive' } }` |
| Auth check | `const session = await auth()` |

## Response Format (Important for Consumers)

`successResponse` wraps data in object:

```typescript
// API returns:
{ success: true, data: T, message?: string }

// Consumer must extract data:
const res = await fetch('/api/items');
const json = await res.json();
const items = json.data;  // Extract from wrapper!

// WRONG
const items = json;  // items is {success, data}, not array!
```

## References

- `route-patterns.md` - Types, pagination, advanced patterns
