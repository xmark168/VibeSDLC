---
name: api-route
description: Create Next.js 16 API Route Handlers. Use when building REST endpoints with GET, POST, PUT, DELETE methods, Zod validation, and proper error handling.
---

# API Route Handler (Next.js 16)

## Critical Rules

1. **File**: `route.ts` in `app/api/` directory
2. **Exports**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
3. **Async params**: MUST `await params` in dynamic routes
4. **Zod validation**: Always validate request body
5. **Error handling**: Use try-catch, return proper status codes

## Quick Reference

### Collection Route
```typescript
// app/api/users/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';
import { successResponse, errorResponse, handleZodError } from '@/lib/api-response';

const schema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function GET(request: NextRequest) {
  try {
    const users = await prisma.user.findMany();
    return successResponse(users);
  } catch (error) {
    return errorResponse('Failed to fetch users', 500);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const validated = schema.safeParse(body);
    if (!validated.success) return handleZodError(validated.error);

    const user = await prisma.user.create({ data: validated.data });
    return successResponse(user, 201);
  } catch (error) {
    return errorResponse('Failed to create user', 500);
  }
}
```

### Dynamic Route (MUST await params)
```typescript
// app/api/users/[id]/route.ts
interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;  // MUST await
  
  const user = await prisma.user.findUnique({ where: { id } });
  if (!user) return errorResponse('Not found', 404);
  
  return successResponse(user);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  await prisma.user.delete({ where: { id } });
  return successResponse({ message: 'Deleted' });
}
```

### API Response Helpers
```typescript
// lib/api-response.ts
export function successResponse<T>(data: T, status = 200) {
  return NextResponse.json({ success: true, data }, { status });
}

export function errorResponse(message: string, status = 400) {
  return NextResponse.json({ success: false, error: message }, { status });
}
```

## Common Patterns

| Pattern | Code |
|---------|------|
| Pagination | `skip: (page-1)*limit, take: limit` |
| Search | `where: { field: { contains: search, mode: 'insensitive' } }` |
| Auth check | `getServerSession(authOptions)` |

## References

- `route-patterns.md` - Advanced patterns, nested routes, auth
