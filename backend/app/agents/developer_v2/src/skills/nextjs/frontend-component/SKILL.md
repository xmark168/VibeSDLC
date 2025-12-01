---
name: frontend-component
description: Create React components for Next.js 16 with proper patterns (client/server components, hooks, shadcn/ui, useActionState)
triggers:
  - component
  - page.tsx
  - client component
  - use client
  - useState
  - useEffect
  - useActionState
  - onClick
  - form
  - button
  - input
  - modal
  - dialog
version: "2.0"
author: VibeSDLC
---

# Frontend Component Skill (Next.js 16 + React 19)

## Critical Rules

1. **Named exports ONLY** - NO default exports (except for pages/layouts)
2. **'use client'** - Required ONLY for hooks, events, browser APIs
3. **Server Components** - Default in Next.js 16, no directive needed
4. **Async params** - Always `await params` and `await searchParams` in pages
5. **Props interface** - Always define TypeScript interface
6. **shadcn/ui** - Use components from `@/components/ui/`
7. **useActionState** - Use for forms with Server Actions (React 19)

## Page Component (MUST await params)

```tsx
// app/users/[id]/page.tsx
import { prisma } from '@/lib/prisma';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

export default async function UserPage({ params, searchParams }: PageProps) {
  // MUST await params - Breaking change in Next.js 15+
  const { id } = await params;
  const { tab } = await searchParams;

  const user = await prisma.user.findUnique({ where: { id } });
  if (!user) notFound();

  return (
    <div>
      <h1>{user.name}</h1>
      {tab === 'posts' && <UserPosts userId={id} />}
    </div>
  );
}
```

## Server Component (Default - No Directive)

```tsx
// components/UserList.tsx - Server Component
import { prisma } from '@/lib/prisma';

interface UserListProps {
  limit?: number;
}

export async function UserList({ limit = 10 }: UserListProps) {
  const users = await prisma.user.findMany({
    take: limit,
    orderBy: { createdAt: 'desc' },
  });

  return (
    <div className="space-y-4">
      {users.map((user) => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
}
```

## Client Component (Only When Needed)

```tsx
// components/Counter.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface CounterProps {
  initialValue?: number;
}

export function Counter({ initialValue = 0 }: CounterProps) {
  const [count, setCount] = useState(initialValue);

  return (
    <div className="flex items-center gap-4">
      <Button variant="outline" onClick={() => setCount(c => c - 1)}>-</Button>
      <span className="text-xl font-semibold">{count}</span>
      <Button variant="outline" onClick={() => setCount(c => c + 1)}>+</Button>
    </div>
  );
}
```

## Form with useActionState (React 19 Pattern)

```tsx
// components/CreateUserForm.tsx
'use client';

import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function CreateUserForm() {
  const [state, formAction, isPending] = useActionState(createUser, null);

  return (
    <form action={formAction} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" name="name" required disabled={isPending} />
        {state?.fieldErrors?.name && (
          <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" required disabled={isPending} />
        {state?.fieldErrors?.email && (
          <p className="text-sm text-destructive">{state.fieldErrors.email[0]}</p>
        )}
      </div>

      <Button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create User'}
      </Button>

      {state?.success && (
        <p className="text-sm text-green-600">User created successfully!</p>
      )}
      {state?.error && !state.fieldErrors && (
        <p className="text-sm text-destructive">{state.error}</p>
      )}
    </form>
  );
}
```

## Form with React Hook Form + Zod (Client-side Validation)

```tsx
// components/UserForm.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
});

type FormValues = z.infer<typeof formSchema>;

interface UserFormProps {
  onSubmit: (data: FormValues) => Promise<void>;
  defaultValues?: Partial<FormValues>;
}

export function UserForm({ onSubmit, defaultValues }: UserFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: '', email: '', ...defaultValues },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Enter name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="Enter email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? 'Saving...' : 'Save'}
        </Button>
      </form>
    </Form>
  );
}
```

## Server + Client Composition

```tsx
// app/users/page.tsx (Server Component)
import { prisma } from '@/lib/prisma';
import { UserCard } from '@/components/UserCard';           // Server
import { DeleteUserButton } from '@/components/DeleteUserButton'; // Client

export default async function UsersPage() {
  const users = await prisma.user.findMany();

  return (
    <div className="space-y-4">
      {users.map((user) => (
        <div key={user.id} className="flex items-center justify-between p-4 border rounded-lg">
          <UserCard user={user} />
          <DeleteUserButton userId={user.id} />
        </div>
      ))}
    </div>
  );
}
```

## Delete Button with useTransition

```tsx
// components/DeleteUserButton.tsx
'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { deleteUser } from '@/app/actions/user';

interface DeleteUserButtonProps {
  userId: string;
}

export function DeleteUserButton({ userId }: DeleteUserButtonProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleDelete = () => {
    if (!confirm('Are you sure?')) return;
    
    startTransition(async () => {
      const result = await deleteUser(userId);
      if (result.success) {
        router.refresh();
      }
    });
  };

  return (
    <Button variant="destructive" size="icon" onClick={handleDelete} disabled={isPending}>
      <Trash2 className="h-4 w-4" />
    </Button>
  );
}
```

## When to Use 'use client'

| Need | Directive |
|------|-----------|
| useState, useEffect, useRef | 'use client' |
| onClick, onChange, onSubmit | 'use client' |
| useRouter, usePathname | 'use client' |
| useActionState, useTransition | 'use client' |
| localStorage, window | 'use client' |
| Fetch data from DB | NO directive (Server) |
| Access env secrets | NO directive (Server) |
| Static rendering | NO directive (Server) |
