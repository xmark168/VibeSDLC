# Advanced Route Patterns

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

  if (!post) return errorResponse('Post not found', 404);
  return successResponse(post);
}
```

## Protected Routes

```typescript
// app/api/admin/users/route.ts
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);

  if (!session) return errorResponse('Unauthorized', 401);
  if (session.user.role !== 'ADMIN') return errorResponse('Forbidden', 403);

  const users = await prisma.user.findMany();
  return successResponse(users);
}
```

## Pagination with Search

```typescript
export async function GET(request: NextRequest) {
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

  const [items, total] = await Promise.all([
    prisma.user.findMany({
      where,
      skip: (page - 1) * limit,
      take: limit,
      orderBy: { createdAt: 'desc' },
    }),
    prisma.user.count({ where }),
  ]);

  return successResponse({ items, total, page, limit });
}
```

## Full API Response Helper

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
