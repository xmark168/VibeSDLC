---
name: authentication
description: Implement authentication with NextAuth v5. Use when adding login/logout, checking sessions, protecting API routes, server actions, or pages.
---

# Authentication (NextAuth v5)

## Critical Rules

1. **Config**: `src/auth.ts` - Already configured in boilerplate
2. **Server-side**: Use `auth()` from `@/auth`
3. **Client-side**: Use `useSession()` from `next-auth/react`
4. **Protect**: Always check session before sensitive operations

## Quick Reference

### Server-side (API Route)
```typescript
import { auth } from '@/auth';
import { ApiErrors } from '@/lib/api-response';

const session = await auth();
if (!session) throw ApiErrors.unauthorized();
const userId = session.user.id;
```

### Server-side (Server Action)
```typescript
'use server';
import { auth } from '@/auth';

const session = await auth();
if (!session) return { success: false, error: 'Unauthorized' };
```

### Server-side (Page)
```tsx
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

const session = await auth();
if (!session) redirect('/login');
```

### Client-side
```tsx
'use client';
import { useSession, signIn, signOut } from 'next-auth/react';

const { data: session, status } = useSession();
if (status === 'loading') return <div>Loading...</div>;
if (session) signOut();
else signIn();
```

### Login Form
```tsx
'use client';
import { signIn } from 'next-auth/react';

const result = await signIn('credentials', {
  username: formData.get('username'),
  password: formData.get('password'),
  redirect: false,
});
if (result?.error) setError('Invalid credentials');
else router.push('/dashboard');
```

## Common Patterns

| Pattern | Code |
|---------|------|
| Check auth | `const session = await auth()` |
| Require auth | `if (!session) throw ApiErrors.unauthorized()` |
| Get user ID | `session.user.id` |
| Check role | `session.user.role === 'ADMIN'` |
| Redirect | `if (!session) redirect('/login')` |

## References

- `auth-patterns.md` - SessionProvider setup, role-based access, login forms
