# Project Guidelines

## Stack
Next.js 16 | React 19.2 | TypeScript | Prisma ORM | NextAuth v5 | Tailwind CSS 4 | shadcn/ui | Jest | Bun

## Architecture (MANDATORY)
```
Prisma Schema → Types → API/Actions → Components → Pages
```

## Naming Conventions
| Type | Convention | Example |
|------|-----------|---------|
| Files | kebab-case | `user-profile.tsx` |
| Components | PascalCase | `UserProfile` |
| Variables | camelCase | `userData` |
| Constants | UPPER_SNAKE | `MAX_ITEMS` |
| Route folders | lowercase | `dashboard` |

## Special Files (Next.js 16)
| File | Purpose |
|------|---------|
| `page.tsx` | Route page |
| `layout.tsx` | Shared layout |
| `loading.tsx` | Loading UI |
| `error.tsx` | Error boundary (must be Client Component) |
| `route.ts` | API endpoint |
| `proxy.ts` | Network proxy (replaces middleware.ts) |
| `not-found.tsx` | 404 page |

## Critical Rules
1. **Named exports ONLY** - No default exports
2. **Server Components default** - Add `'use client'` only when using hooks
3. **Zod validation** - Always validate on server
4. **Revalidate** - Call `revalidatePath`/`revalidateTag` after mutations
5. **Append only** - Don't overwrite existing types/models
6. **Prisma generate** - Run after schema changes

## Import Paths
```typescript
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';
```

## API Response Functions
| Function | Status | Usage |
|----------|--------|-------|
| `successResponse(data)` | 200 | Success |
| `successResponse(data, msg, 201)` | 201 | Created |
| `handleError(error)` | varies | Catch-all |
| `ApiErrors.notFound(resource)` | 404 | Not found |
| `ApiErrors.badRequest(msg)` | 400 | Bad request |
| `ApiErrors.unauthorized()` | 401 | Not logged in |

## Component Patterns

### Client Component (hooks required)
```tsx
'use client';
import { useState } from 'react';
export function MyComponent() {
  const [state, setState] = useState('');
  return <div>{state}</div>;
}
```

### Server Component (default)
```tsx
import { prisma } from '@/lib/prisma';
export async function ProductList() {
  const products = await prisma.product.findMany();
  return <div>{/* render */}</div>;
}
```

## API Route Pattern
```typescript
import { NextRequest } from 'next/server';
import { successResponse, handleError } from '@/lib/api-response';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    const data = await prisma.model.findMany();
    return successResponse(data);
  } catch (error) {
    return handleError(error);
  }
}
```

## Server Action Pattern
```typescript
'use server';
import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/prisma';
import { mySchema } from '@/types/api.types';

export async function createItem(formData: FormData) {
  const validated = mySchema.safeParse(Object.fromEntries(formData));
  if (!validated.success) return { error: validated.error.flatten() };
  
  const item = await prisma.item.create({ data: validated.data });
  revalidatePath('/items');
  return { success: true, data: item };
}
```

## Type Definition Pattern
```typescript
import { z } from 'zod';

export const itemSchema = z.object({
  name: z.string().min(1),
  price: z.number().positive(),
});

export type ItemRequest = z.infer<typeof itemSchema>;

export interface Item {
  id: string;
  name: string;
  price: number;
  createdAt: Date;
}
```

## Testing Rules
- **Jest only** - NO vitest
- **Named imports** - No default imports
- **Mock before imports** - `jest.mock()` at top
- **Full URL in Request** - `new Request('http://localhost/api/...')`

### Test Pattern
```typescript
jest.mock('@/lib/prisma', () => ({
  prisma: { model: { findMany: jest.fn() } }
}));

import { GET } from '@/app/api/route';
import { prisma } from '@/lib/prisma';

describe('API', () => {
  it('returns data', async () => {
    (prisma.model.findMany as jest.Mock).mockResolvedValue([]);
    const req = new Request('http://localhost/api/route');
    const res = await GET(req);
    expect(res.status).toBe(200);
  });
});
```

## Directory Structure
```
src/
├── app/
│   ├── api/          # API routes
│   ├── (auth)/       # Auth routes group
│   └── page.tsx      # Home page
├── components/
│   └── ui/           # shadcn/ui
├── actions/          # Server Actions
├── lib/              # Utilities
├── types/            # TypeScript types
└── __tests__/        # Tests
```

## Commands
```bash
bun dev              # Development
bun test             # Run tests
bunx prisma generate # Generate Prisma client
bunx prisma db push  # Push schema to DB
```
