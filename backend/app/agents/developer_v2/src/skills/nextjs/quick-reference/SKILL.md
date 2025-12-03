---
name: quick-reference
description: Quick lookup for common patterns. Use when needing syntax for imports, components, or common operations.
---

# Quick Reference

## Directives

| Type | Syntax | Location |
|------|--------|----------|
| Client Component | `'use client';` | First line |
| Server Action | `'use server';` | First line |

## Common Imports

```typescript
// Auth
import { auth } from '@/auth';
import { signIn, signOut, useSession } from 'next-auth/react';

// Database
import { prisma } from '@/lib/prisma';

// Navigation
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { redirect } from 'next/navigation';
import Link from 'next/link';

// Server
import { revalidatePath, revalidateTag } from 'next/cache';
import { NextRequest } from 'next/server';

// API Response
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';

// UI
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

// Forms
import { useActionState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
```

## Patterns

### Auth Check (Server)
```typescript
const session = await auth();
if (!session) throw ApiErrors.unauthorized();
const userId = session.user.id;
```

### Auth Check (Client)
```typescript
const { data: session, status } = useSession();
if (status === 'loading') return <Spinner />;
if (!session) redirect('/login');
```

### Dynamic Route Params
```typescript
// Next.js 16 - MUST await
interface Props {
  params: Promise<{ id: string }>;
}

export default async function Page({ params }: Props) {
  const { id } = await params;
}
```

### Zod Validation
```typescript
const schema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

const result = schema.safeParse(data);
if (!result.success) {
  return handleError(result.error);
}
const validated = result.data;
```

### Server Action Result
```typescript
type ActionResult<T = void> = 
  | { success: true; data?: T }
  | { success: false; error: string; fieldErrors?: Record<string, string[]> };
```

### API Route Structure
```typescript
export async function GET(request: NextRequest) {
  try {
    // ... logic
    return successResponse(data);
  } catch (error) {
    return handleError(error);
  }
}
```

### Form with useActionState
```tsx
const [state, action, pending] = useActionState(serverAction, null);

<form action={action}>
  <input name="field" disabled={pending} />
  <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
</form>
```

## File Locations

| Type | Path |
|------|------|
| Page | `src/app/[route]/page.tsx` |
| Layout | `src/app/[route]/layout.tsx` |
| API Route | `src/app/api/[resource]/route.ts` |
| Server Action | `src/app/actions/[domain].ts` |
| Component | `src/components/[Feature]/Name.tsx` |
| UI Component | `src/components/ui/name.tsx` |
| Utility | `src/lib/utils.ts` |
| Type | `src/types/[domain].ts` |

## Commands

```bash
bun run dev           # Start dev server
bun run build         # Build for production
bun run test          # Run tests
bun run lint:fix      # Fix lint issues
bunx prisma generate  # Generate Prisma client
bunx prisma db push   # Push schema to DB
bunx prisma studio    # Open Prisma Studio
```
