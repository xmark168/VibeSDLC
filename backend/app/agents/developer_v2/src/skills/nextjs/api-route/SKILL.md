---
name: api-route
description: Create Next.js 16 API Route Handlers. Use when building REST endpoints (GET, POST, PUT, DELETE), implementing CRUD operations, or creating authenticated APIs with Zod validation.
---

This skill guides creation of API Route Handlers in Next.js 16 App Router.

The user needs to build REST endpoints for data operations, typically CRUD functionality with authentication and validation.

## Before You Start

API routes live in the `app/api/` directory:
- **Collection routes**: `app/api/users/route.ts` - handles GET (list) and POST (create)
- **Resource routes**: `app/api/users/[id]/route.ts` - handles GET (one), PUT, DELETE
- **Export functions**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

**CRITICAL**: In Next.js 16, dynamic route params are async. You MUST `await params` before using them.

## Prisma Relationship Matching

**CRITICAL**: Field names trong `include` PHẢI khớp CHÍNH XÁC với schema:

| Schema định nghĩa | Query sử dụng | ✅/❌ |
|-------------------|---------------|------|
| `categories Category[]` | `include: { categories: true }` | ✅ |
| `categories Category[]` | `include: { category: true }` | ❌ WRONG |
| `category Category` | `include: { category: true }` | ✅ |

**Rule**: 
- Many-to-many/One-to-many → **PLURAL** (categories, tags, posts)
- One-to-one/Many-to-one → **SINGULAR** (category, user, author)

## Route Structure

### Collection Route (List + Create)

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

### Dynamic Route (Single Resource)

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
    const { id } = await context.params;  // MUST await in Next.js 16
    
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

The `handleError()` function catches all error types automatically:
- **ZodError**: Returns 422 with formatted field errors
- **ApiException**: Returns custom status with error code
- **Generic Error**: Returns 500 with message

Use predefined errors for common cases:

```typescript
throw ApiErrors.unauthorized();      // 401 - Not logged in
throw ApiErrors.forbidden();         // 403 - No permission
throw ApiErrors.notFound('User');    // 404 - Resource not found
throw ApiErrors.badRequest('msg');   // 400 - Invalid request
throw ApiErrors.conflict('msg');     // 409 - Already exists
throw ApiErrors.validation('msg');   // 422 - Validation failed
```

## Response Format

**IMPORTANT**: `successResponse()` always wraps data in an object. Consumers must extract `.data`:

```typescript
// API returns this format:
{ success: true, data: T, message?: string }

// Consumer code:
const res = await fetch('/api/items');
const json = await res.json();
const items = json.data;  // Extract from wrapper!

// NOT this (common mistake):
const items = json;  // Wrong! json is {success, data}, not the array
```

## Handling Decimal Fields

Prisma `Decimal` type doesn't serialize to JSON as number. Convert before response:

```typescript
// Single item
const item = await prisma.item.findUnique({ where: { id } });
return successResponse({
  ...item,
  price: Number(item.price),  // Convert Decimal to number
});

// List of items
const items = await prisma.item.findMany();
return successResponse(
  items.map(item => ({
    ...item,
    price: Number(item.price),
  }))
);
```

**Tip**: Use `Float` instead of `Decimal` in schema to avoid this conversion entirely.

## Common Patterns

- **Search**: Use `where: { field: { contains: query, mode: 'insensitive' } }`
- **Auth check**: Always `const session = await auth()` before mutations
- **Validation**: Always use Zod schema with `safeParse()` for request body

## Pagination Pattern

For list endpoints, always support pagination:

```typescript
// app/api/items/route.ts
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get('page') ?? '1');
    const limit = parseInt(searchParams.get('limit') ?? '20');
    const skip = (page - 1) * limit;

    const [items, total] = await Promise.all([
      prisma.item.findMany({
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
      prisma.item.count(),
    ]);

    return successResponse({
      items,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    return handleError(error);
  }
}
```

**Rules:**
- Default limit: 20 items
- Always return `total` count for frontend pagination UI
- Use `Promise.all` for parallel queries

## After Writing Route

Validation (typecheck, lint, tests) runs automatically at the end of implementation.
No need to run manually - proceed to next file.

NEVER:
- Skip `await` on `context.params` in dynamic routes
- Return raw data without `successResponse()` wrapper
- Skip validation on POST/PUT request bodies
- Forget auth checks on mutation endpoints

**IMPORTANT**: Always wrap route logic in try-catch and use `handleError()` for consistent error responses.
