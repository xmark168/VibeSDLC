---
name: authentication
description: Implement authentication with NextAuth v5. Use when adding login/logout, checking sessions, protecting API routes, server actions, or pages.
---

This skill guides implementation of authentication using NextAuth v5, which is pre-configured in the boilerplate.

The user needs to protect routes, verify sessions, implement login/logout, or add role-based access control.

## Before You Start

The authentication system is already configured:
- **Config file**: `src/auth.ts` - Contains NextAuth configuration
- **Prisma adapter**: User, Account, Session models in schema
- **Credentials provider**: Username/password authentication ready

**CRITICAL**: Always check session before sensitive operations. Never trust client-side auth state for security decisions.

## Server-Side Authentication

Use `auth()` from `@/auth` for all server-side auth checks:

```typescript
import { auth } from '@/auth';
import { ApiErrors } from '@/lib/api-response';

// In API routes
const session = await auth();
if (!session) throw ApiErrors.unauthorized();
const userId = session.user.id;
```

```typescript
// In Server Actions
'use server';
import { auth } from '@/auth';

const session = await auth();
if (!session) return { success: false, error: 'Unauthorized' };
```

```tsx
// In Pages (Server Component)
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

const session = await auth();
if (!session) redirect('/login');
```

## Client-Side Authentication

Use `useSession()` from `next-auth/react` for client components:

```tsx
'use client';
import { useSession, signIn, signOut } from 'next-auth/react';

export function AuthButton() {
  const { data: session, status } = useSession();
  
  if (status === 'loading') return <div>Loading...</div>;
  
  if (session) {
    return (
      <div>
        <span>{session.user.username}</span>
        <button onClick={() => signOut()}>Sign Out</button>
      </div>
    );
  }
  
  return <button onClick={() => signIn()}>Sign In</button>;
}
```

## Login Form Implementation

```tsx
'use client';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState('');
  
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const result = await signIn('credentials', {
      username: formData.get('username'),
      password: formData.get('password'),
      redirect: false,
    });
    
    if (result?.error) {
      setError('Invalid credentials');
    } else {
      router.push('/dashboard');
    }
  }
  
  return (
    <form onSubmit={handleSubmit}>
      <input name="username" placeholder="Username" required />
      <input name="password" type="password" placeholder="Password" required />
      {error && <p className="text-destructive">{error}</p>}
      <button type="submit">Login</button>
    </form>
  );
}
```

## Role-Based Access

Check user roles for authorization:

```typescript
// In API Route
const session = await auth();
if (!session) throw ApiErrors.unauthorized();
if (session.user.role !== 'ADMIN') throw ApiErrors.forbidden();

// In Server Component
const session = await auth();
if (session?.user.role !== 'ADMIN') {
  return <div>Access denied</div>;
}
return <AdminPanel />;
```

## Common Patterns

- **Get current user ID**: `session.user.id`
- **Check if logged in**: `if (!session) throw ApiErrors.unauthorized()`
- **Check role**: `session.user.role === 'ADMIN'`
- **Redirect unauthenticated**: `if (!session) redirect('/login')`
- **Client loading state**: `if (status === 'loading') return <Spinner />`

NEVER:
- Trust client-side session for security decisions
- Store sensitive data in session
- Skip auth checks in API routes that modify data
- Use `useSession` in Server Components

**IMPORTANT**: The SessionProvider is already configured in the boilerplate layout. You don't need to add it again.
