# Authentication Patterns

## SessionProvider Setup

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
```

```tsx
// components/SessionProvider.tsx
'use client';

import { SessionProvider as Provider } from 'next-auth/react';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  return <Provider>{children}</Provider>;
}
```

## Complete Login Form

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

## Role-based Access

### In API Route
```typescript
import { auth } from '@/auth';
import { ApiErrors } from '@/lib/api-response';

const session = await auth();
if (!session) throw ApiErrors.unauthorized();
if (session.user.role !== 'ADMIN') throw ApiErrors.forbidden();
```

### In Component
```tsx
import { auth } from '@/auth';

export default async function AdminPage() {
  const session = await auth();
  
  if (session?.user.role === 'ADMIN') {
    return <AdminPanel />;
  }
  
  return <div>Access denied</div>;
}
```

## Auth Buttons Component

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

## Protected API Route (Full Example)

```typescript
// app/api/protected/route.ts
import { NextRequest } from 'next/server';
import { auth } from '@/auth';
import { ApiErrors, handleError, successResponse } from '@/lib/api-response';

export async function GET(request: NextRequest) {
  try {
    const session = await auth();
    if (!session) throw ApiErrors.unauthorized();
    
    const userId = session.user.id;
    
    return successResponse({ userId, message: 'Authenticated!' });
  } catch (error) {
    return handleError(error);
  }
}
```
