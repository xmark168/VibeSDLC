---
name: api-route
description: Create Next.js 16 API Route Handlers with async params, Zod validation, and proper error handling
triggers:
  - api
  - route.ts
  - route handler
  - GET
  - POST
  - PUT
  - DELETE
  - PATCH
  - endpoint
  - REST
version: "2.0"
author: VibeSDLC
---

# API Route Handler Skill (Next.js 16)

## Critical Rules

1. **File naming**: `route.ts` in `app/api/` directory
2. **Export HTTP methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
3. **Async params**: MUST `await params` in dynamic routes (Next.js 15+ breaking change)
4. **Zod validation**: Always validate request body
5. **Use helpers**: Use `successResponse`, `errorResponse` from `@/lib/api-response`
6. **Error handling**: Wrap in try-catch, return proper status codes

## Basic Route Handler (Collection)

```typescript
// app/api/users/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';
import { successResponse, errorResponse, handleZodError } from '@/lib/api-response';

const createUserSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  role: z.enum(['USER', 'ADMIN']).default('USER'),
});

// GET /api/users
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '10');
    const search = searchParams.get('search') || '';

    const where = search ? {
      OR: [
        { name: { contains: search, mode: 'insensitive' as const } },
        { email: { contains: search, mode: 'insensitive' as const } },
      ],
    } : undefined;

    const [users, total] = await Promise.all([
      prisma.user.findMany({
        where,
        skip: (page - 1) * limit,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
      prisma.user.count({ where }),
    ]);

    return successResponse({ users, total, page, limit });
  } catch (error) {
    console.error('[GET /api/users]', error);
    return errorResponse('Failed to fetch users', 500);
  }
}

// POST /api/users
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const validated = createUserSchema.safeParse(body);

    if (!validated.success) {
      return handleZodError(validated.error);
    }

    const user = await prisma.user.create({
      data: validated.data,
    });

    return successResponse(user, 201);
  } catch (error) {
    console.error('[POST /api/users]', error);
    return errorResponse('Failed to create user', 500);
  }
}
```

## Dynamic Route Handler (MUST await params)

```typescript
// app/api/users/[id]/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';
import { successResponse, errorResponse, handleZodError } from '@/lib/api-response';

// CRITICAL: params is now a Promise in Next.js 15+
interface RouteContext {
  params: Promise<{ id: string }>;
}

const updateUserSchema = z.object({
  name: z.string().min(2).optional(),
  email: z.string().email().optional(),
  role: z.enum(['USER', 'ADMIN']).optional(),
});

// GET /api/users/[id]
export async function GET(request: NextRequest, context: RouteContext) {
  // MUST await params - Breaking change in Next.js 15+
  const { id } = await context.params;

  try {
    const user = await prisma.user.findUnique({ where: { id } });

    if (!user) {
      return errorResponse('User not found', 404);
    }

    return successResponse(user);
  } catch (error) {
    console.error(`[GET /api/users/${id}]`, error);
    return errorResponse('Failed to fetch user', 500);
  }
}

// PUT /api/users/[id]
export async function PUT(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;

  try {
    const body = await request.json();
    const validated = updateUserSchema.safeParse(body);

    if (!validated.success) {
      return handleZodError(validated.error);
    }

    const user = await prisma.user.update({
      where: { id },
      data: validated.data,
    });

    return successResponse(user);
  } catch (error) {
    console.error(`[PUT /api/users/${id}]`, error);
    return errorResponse('Failed to update user', 500);
  }
}

// DELETE /api/users/[id]
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;

  try {
    await prisma.user.delete({ where: { id } });
    return successResponse({ message: 'User deleted successfully' });
  } catch (error) {
    console.error(`[DELETE /api/users/${id}]`, error);
    return errorResponse('Failed to delete user', 500);
  }
}
```

## API Response Helpers

```typescript
// lib/api-response.ts
import { NextResponse } from 'next/server';
import { ZodError } from 'zod';

export function successResponse<T>(data: T, status = 200) {
  return NextResponse.json({ success: true, data }, { status });
}

export function errorResponse(message: string, status = 400) {
  return NextResponse.json({ success: false, error: message }, { status });
}

export function handleZodError(error: ZodError) {
  return NextResponse.json(
    {
      success: false,
      error: 'Validation failed',
      details: error.flatten().fieldErrors,
    },
    { status: 400 }
  );
}

export class ApiException extends Error {
  constructor(public message: string, public status: number = 400) {
    super(message);
  }
}
```

## Nested Dynamic Routes

```typescript
// app/api/users/[userId]/posts/[postId]/route.ts
interface RouteContext {
  params: Promise<{ userId: string; postId: string }>;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { userId, postId } = await context.params;

  const post = await prisma.post.findFirst({
    where: { id: postId, authorId: userId },
  });

  if (!post) {
    return errorResponse('Post not found', 404);
  }

  return successResponse(post);
}
```

## Protected Routes (Auth Check)

```typescript
// app/api/admin/users/route.ts
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);

  if (!session) {
    return errorResponse('Unauthorized', 401);
  }

  if (session.user.role !== 'ADMIN') {
    return errorResponse('Forbidden', 403);
  }

  const users = await prisma.user.findMany();
  return successResponse(users);
}
```

## Common Patterns

| Pattern | Implementation |
|---------|---------------|
| Pagination | `skip: (page-1)*limit, take: limit` |
| Search | `where: { field: { contains: search, mode: 'insensitive' } }` |
| Sort | `orderBy: { field: 'asc' \| 'desc' }` |
| Include relations | `include: { posts: true }` |
| Select fields | `select: { id: true, name: true }` |
