---
name: server-action
description: Create Next.js 16 Server Actions with useActionState, Zod validation, and proper error handling
triggers:
  - server action
  - use server
  - action
  - form action
  - revalidatePath
  - revalidateTag
  - mutation
  - useActionState
version: "2.0"
author: VibeSDLC
---

# Server Action Skill (Next.js 16 + React 19)

## Critical Rules

1. **'use server'** - Required at top of file
2. **File location** - Put in `app/actions/` directory
3. **Zod validation** - Always validate FormData with Zod
4. **Return ActionResult** - Consistent return type for client handling
5. **revalidatePath** - Call after successful mutations
6. **useActionState** - Use in client components (React 19)

## ActionResult Type Pattern

```typescript
// types/action.types.ts
export type ActionResult<T = void> = 
  | { success: true; data?: T }
  | { success: false; error: string; fieldErrors?: Record<string, string[]> };
```

## Basic Server Action

```typescript
// app/actions/user.ts
'use server';

import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

// Zod schema for validation
const createUserSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
});

// ActionResult type
type ActionResult<T = void> = 
  | { success: true; data?: T }
  | { success: false; error: string; fieldErrors?: Record<string, string[]> };

export async function createUser(
  prevState: ActionResult | null,
  formData: FormData
): Promise<ActionResult<{ id: string }>> {
  // Extract data from FormData
  const rawData = {
    name: formData.get('name') as string,
    email: formData.get('email') as string,
  };

  // Validate with Zod
  const validated = createUserSchema.safeParse(rawData);
  if (!validated.success) {
    return {
      success: false,
      error: 'Validation failed',
      fieldErrors: validated.error.flatten().fieldErrors,
    };
  }

  try {
    const user = await prisma.user.create({
      data: validated.data,
    });

    revalidatePath('/users');
    return { success: true, data: { id: user.id } };
  } catch (error) {
    console.error('[createUser]', error);
    return { success: false, error: 'Failed to create user' };
  }
}

export async function deleteUser(id: string): Promise<ActionResult> {
  try {
    await prisma.user.delete({ where: { id } });
    revalidatePath('/users');
    return { success: true };
  } catch (error) {
    console.error('[deleteUser]', error);
    return { success: false, error: 'Failed to delete user' };
  }
}

export async function updateUser(
  id: string,
  formData: FormData
): Promise<ActionResult<{ id: string; name: string }>> {
  const rawData = {
    name: formData.get('name') as string,
    email: formData.get('email') as string,
  };

  const validated = createUserSchema.safeParse(rawData);
  if (!validated.success) {
    return {
      success: false,
      error: 'Validation failed',
      fieldErrors: validated.error.flatten().fieldErrors,
    };
  }

  try {
    const user = await prisma.user.update({
      where: { id },
      data: validated.data,
      select: { id: true, name: true },
    });

    revalidatePath('/users');
    revalidatePath(`/users/${id}`);
    return { success: true, data: user };
  } catch (error) {
    console.error('[updateUser]', error);
    return { success: false, error: 'Failed to update user' };
  }
}
```

## Form with useActionState (React 19)

```tsx
// components/CreateUserForm.tsx
'use client';

import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function CreateUserForm() {
  // useActionState returns [state, formAction, isPending]
  const [state, formAction, isPending] = useActionState(createUser, null);

  return (
    <form action={formAction} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          name="name"
          placeholder="Enter name"
          required
          disabled={isPending}
        />
        {state?.fieldErrors?.name && (
          <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          placeholder="Enter email"
          required
          disabled={isPending}
        />
        {state?.fieldErrors?.email && (
          <p className="text-sm text-destructive">{state.fieldErrors.email[0]}</p>
        )}
      </div>

      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? 'Creating...' : 'Create User'}
      </Button>

      {state?.success && (
        <Alert>
          <AlertDescription>User created successfully!</AlertDescription>
        </Alert>
      )}

      {state?.error && !state.fieldErrors && (
        <Alert variant="destructive">
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
```

## Delete Action with useTransition

```tsx
// components/DeleteUserButton.tsx
'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Trash2, Loader2 } from 'lucide-react';
import { deleteUser } from '@/app/actions/user';
import { toast } from 'sonner';

interface DeleteUserButtonProps {
  userId: string;
  userName: string;
}

export function DeleteUserButton({ userId, userName }: DeleteUserButtonProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleDelete = () => {
    if (!confirm(`Delete user "${userName}"?`)) return;

    startTransition(async () => {
      const result = await deleteUser(userId);

      if (result.success) {
        toast.success('User deleted successfully');
        router.refresh();
      } else {
        toast.error(result.error);
      }
    });
  };

  return (
    <Button
      variant="destructive"
      size="icon"
      onClick={handleDelete}
      disabled={isPending}
    >
      {isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Trash2 className="h-4 w-4" />
      )}
    </Button>
  );
}
```

## Action with Redirect

```typescript
// app/actions/post.ts
'use server';

import { prisma } from '@/lib/prisma';
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const createPostSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  content: z.string().min(10, 'Content must be at least 10 characters'),
});

export async function createPost(formData: FormData) {
  const rawData = {
    title: formData.get('title') as string,
    content: formData.get('content') as string,
  };

  const validated = createPostSchema.safeParse(rawData);
  if (!validated.success) {
    return {
      success: false,
      error: 'Validation failed',
      fieldErrors: validated.error.flatten().fieldErrors,
    };
  }

  const post = await prisma.post.create({
    data: validated.data,
  });

  revalidatePath('/posts');
  redirect(`/posts/${post.id}`);
}
```

## Inline Action in Page (MUST await params)

```tsx
// app/posts/[id]/page.tsx
import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { Button } from '@/components/ui/button';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PostPage({ params }: PageProps) {
  // MUST await params in Next.js 15+
  const { id } = await params;
  const post = await prisma.post.findUnique({ where: { id } });

  if (!post) {
    redirect('/posts');
  }

  async function deletePost() {
    'use server';
    await prisma.post.delete({ where: { id } });
    revalidatePath('/posts');
    redirect('/posts');
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{post.title}</h1>
      <p>{post.content}</p>
      <form action={deletePost}>
        <Button type="submit" variant="destructive">
          Delete Post
        </Button>
      </form>
    </div>
  );
}
```

## Best Practices Summary

| Practice | Description |
|----------|-------------|
| File organization | Group by domain: `actions/user.ts`, `actions/post.ts` |
| Type safety | Always use `ActionResult<T>` return type |
| Validation | Use Zod with `.safeParse()`, return fieldErrors |
| Error handling | Return error state, never throw |
| Revalidation | Use specific paths: `revalidatePath('/users')` |
| Client integration | Use `useActionState` for forms, `useTransition` for buttons |
