# API Route Patterns

## ⚠️ Response Format Rules - CRITICAL

**LUÔN trả về array trực tiếp trong `data`, KHÔNG wrap trong object:**

```typescript
//  CORRECT - data is array
return successResponse(items);
// Result: { success: true, data: [...] }

// WRONG - data is object with nested array
return successResponse({ results: items, metadata: {...} });
// Result: { success: true, data: { results: [...], metadata: {...} } }
// Frontend sẽ CRASH khi gọi data.data.map()!
```

**Nếu cần metadata (pagination, filters), dùng `meta` field riêng:**

```typescript
//  CORRECT with meta
return NextResponse.json({
  success: true,
  data: items,           // Array trực tiếp
  meta: {                // Metadata riêng
    total,
    page,
    limit,
    appliedFilters: {...}
  }
});
```

---

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

## Search with Filters Pattern

**CRITICAL**: Param names MUST match frontend exactly!

```typescript
// app/api/books/search/route.ts
import { NextRequest } from 'next/server';
import { Prisma } from '@prisma/client';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError } from '@/lib/api-response';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // Parse comma-separated filters (NOT getAll!)
    const categories = searchParams.get('categories')?.split(',').filter(Boolean) ?? [];
    const authors = searchParams.get('authors')?.split(',').filter(Boolean) ?? [];
    const minPrice = searchParams.get('minPrice');
    const maxPrice = searchParams.get('maxPrice');
    const sort = searchParams.get('sort') || 'relevance';  // NOT 'sortBy'!
    const query = searchParams.get('q') || '';

    // Build Prisma where clause
    const where: Prisma.BookWhereInput = {};
    
    if (query) {
      where.OR = [
        { title: { contains: query, mode: 'insensitive' } },
        { author: { name: { contains: query, mode: 'insensitive' } } },
      ];
    }
    
    if (categories.length > 0) {
      where.categoryId = { in: categories };
    }
    
    if (authors.length > 0) {
      where.authorId = { in: authors };
    }
    
    if (minPrice || maxPrice) {
      where.price = {};
      if (minPrice) where.price.gte = parseFloat(minPrice);
      if (maxPrice) where.price.lte = parseFloat(maxPrice);
    }

    // Sort mapping - use 'sort' param, NOT 'sortBy'
    const orderByMap: Record<string, Prisma.BookOrderByWithRelationInput> = {
      'price-asc': { price: 'asc' },
      'price-desc': { price: 'desc' },
      'newest': { createdAt: 'desc' },
      'title': { title: 'asc' },
      'relevance': { title: 'asc' },
    };
    const orderBy = orderByMap[sort] || { title: 'asc' };

    const books = await prisma.book.findMany({
      where,
      orderBy,
      include: {
        author: { select: { id: true, name: true } },
        category: { select: { id: true, name: true } },
      },
    });

    // Convert Decimal to number if needed
    const result = books.map(book => ({
      ...book,
      price: Number(book.price),
    }));

    return successResponse(result);
  } catch (error) {
    return handleError(error);
  }
}
```

**Param naming convention:**
- Multi-select: `categories`, `authors`, `tags` (plural, comma-separated)
- Single value: `sort`, `page`, `limit`
- Range: `minPrice`, `maxPrice`
