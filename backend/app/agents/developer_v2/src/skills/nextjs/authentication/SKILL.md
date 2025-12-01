---
name: authentication
description: Implement authentication with NextAuth v5. Use when adding login, logout, session checks, or protecting routes and API endpoints.
---

# Authentication (NextAuth v5)

## Critical Rules

1. **Config**: `src/auth.ts` - Main NextAuth configuration
2. **Route**: `app/api/auth/[...nextauth]/route.ts` - Already setup
3. **Session**: Use `auth()` for server-side, `useSession()` for client
4. **Protect**: Always check session before sensitive operations

## Quick Reference

### Check Auth in API Route
```typescript
// app/api/protected/route.ts
import { auth } from '@/auth';
import { ApiErrors, handleError, successResponse } from '@/lib/api-response';

export async function GET() {
  try {
    const session = await auth();
    if (!session) throw ApiErrors.unauthorized();
    
    // Access user data
    const userId = session.user.id;
    
    return successResponse({ userId });
  } catch (error) {
    return handleError(error);
  }
}
```

### Check Auth in Server Action
```typescript
// app/actions/protected.ts
'use server';

import { auth } from '@/auth';

export async function protectedAction(formData: FormData) {
  const session = await auth();
  if (!session) {
    return { success: false, error: 'Unauthorized' };
  }
  
  // Proceed with action
  return { success: true };
}
```

### Check Auth in Server Component
```tsx
// app/dashboard/page.tsx
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect('/login');
  
  return <div>Welcome {session.user.username}</div>;
}
```

### Client-side Auth
```tsx
'use client';

import { useSession, signIn, signOut } from 'next-auth/react';

export function AuthButtons() {
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

### Login Form
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

## Session Provider Setup

```tsx
// app/layout.tsx
import { SessionProvider } from '@/components/SessionProvider';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}

// components/SessionProvider.tsx
'use client';

import { SessionProvider as Provider } from 'next-auth/react';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  return <Provider>{children}</Provider>;
}
```

## Role-based Access

```typescript
// Check role in API
const session = await auth();
if (!session) throw ApiErrors.unauthorized();
if (session.user.role !== 'ADMIN') throw ApiErrors.forbidden();

// Check role in component
if (session.user.role === 'ADMIN') {
  return <AdminPanel />;
}
```
