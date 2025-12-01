# API Route Patterns

## Types (from api.types.ts)

```typescript
// Response wrapper
interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
  meta?: PaginationMeta;
}

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

// HTTP Status
enum HttpStatus {
  OK = 200,
  CREATED = 201,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  UNPROCESSABLE_ENTITY = 422,
  INTERNAL_SERVER_ERROR = 500,
}

// Error Codes
enum ApiErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
}
```

## Pagination Pattern

```typescript
// app/api/items/route.ts
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError } from '@/lib/api-response';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '10');
    const search = searchParams.get('q') || '';

    const where = search
      ? { name: { contains: search, mode: 'insensitive' as const } }
      : {};

    const [items, total] = await Promise.all([
      prisma.item.findMany({
        where,
        skip: (page - 1) * limit,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
      prisma.item.count({ where }),
    ]);

    return NextResponse.json({
      success: true,
      data: items,
      meta: {
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

## Auth Protected Route

```typescript
import { auth } from '@/auth';
import { ApiErrors } from '@/lib/api-response';

export async function POST(request: NextRequest) {
  try {
    const session = await auth();
    if (!session) throw ApiErrors.unauthorized();
    
    // Only admins
    if (session.user.role !== 'ADMIN') throw ApiErrors.forbidden();
    
    // ... rest of handler
  } catch (error) {
    return handleError(error);
  }
}
```

## Predefined ApiErrors

```typescript
// lib/api-response.ts exports:
ApiErrors.unauthorized()        // 401 - Need login
ApiErrors.forbidden()           // 403 - No permission
ApiErrors.notFound('Resource')  // 404 - Not found
ApiErrors.badRequest('msg')     // 400 - Bad request
ApiErrors.conflict('msg')       // 409 - Conflict
ApiErrors.validation('msg')     // 422 - Validation error
ApiErrors.tooManyRequests()     // 429 - Rate limit
ApiErrors.database('msg')       // 500 - DB error
```

## File Upload

```typescript
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) throw ApiErrors.badRequest('No file provided');
    
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    
    // Save to disk or cloud storage
    // ...
    
    return successResponse({ filename: file.name });
  } catch (error) {
    return handleError(error);
  }
}
```
