---
name: server-action
description: Create Next.js 16 Server Actions. Use when building form handlers, mutations with Zod validation, or data operations that need useActionState and revalidatePath.
---

This skill guides creation of Server Actions in Next.js 16 with React 19.

The user needs to handle form submissions, create mutations, or perform server-side operations triggered from client components.

## Before You Start

Server Actions are the preferred way to handle mutations in Next.js:
- **File location**: `app/actions/[domain].ts` (e.g., `app/actions/user.ts`)
- **Directive**: Must have `'use server'` at top of file
- **Return type**: Always return `ActionResult` for consistent handling

**CRITICAL**: Server Actions run on the server. They can access the database directly but must validate all input.

## ActionResult Type

Always use this consistent return type:

```typescript
type ActionResult<T = void> = 
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

const schema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function createUser(
  prevState: ActionResult | null,
  formData: FormData
): Promise<ActionResult<{ id: string }>> {
  const validated = schema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  });

  if (!validated.success) {
    return {
      success: false,
      error: 'Validation failed',
      fieldErrors: validated.error.flatten().fieldErrors,
    };
  }

  try {
    const user = await prisma.user.create({ data: validated.data });
    revalidatePath('/users');
    return { success: true, data: { id: user.id } };
  } catch (error) {
    return { success: false, error: 'Failed to create user' };
  }
}

export async function deleteUser(id: string): Promise<ActionResult> {
  try {
    await prisma.user.delete({ where: { id } });
    revalidatePath('/users');
    return { success: true };
  } catch (error) {
    return { success: false, error: 'Failed to delete' };
  }
}
```

## Using with useActionState

The `useActionState` hook connects forms to Server Actions with automatic pending state:

```tsx
'use client';
import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';

export function CreateForm() {
  const [state, action, pending] = useActionState(createUser, null);

  return (
    <form action={action}>
      <input name="name" disabled={pending} />
      {state?.fieldErrors?.name && <p>{state.fieldErrors.name[0]}</p>}
      
      <input name="email" disabled={pending} />
      {state?.fieldErrors?.email && <p>{state.fieldErrors.email[0]}</p>}
      
      <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
      
      {state?.error && !state.fieldErrors && (
        <p className="text-destructive">{state.error}</p>
      )}
    </form>
  );
}
```

## Using with useTransition

For non-form actions (like delete buttons), use `useTransition`:

```tsx
'use client';
import { useTransition } from 'react';
import { deleteUser } from '@/app/actions/user';

export function DeleteButton({ id }: { id: string }) {
  const [pending, startTransition] = useTransition();

  return (
    <button
      onClick={() => startTransition(() => deleteUser(id))}
      disabled={pending}
    >
      {pending ? 'Deleting...' : 'Delete'}
    </button>
  );
}
```

## Adding Authentication

Check session in actions that require authentication:

```typescript
'use server';
import { auth } from '@/auth';

export async function createPost(
  prevState: ActionResult | null,
  formData: FormData
): Promise<ActionResult> {
  const session = await auth();
  if (!session) {
    return { success: false, error: 'Unauthorized' };
  }

  // ... rest of action using session.user.id
}
```

## Common Patterns

- **Revalidate after mutation**: Always call `revalidatePath('/path')` after changing data
- **Redirect after success**: Use `redirect('/path')` from `next/navigation`
- **Field errors**: Return `fieldErrors` object matching form field names
- **Auth check**: `const session = await auth(); if (!session) return error`

## After Writing Action

Run validation to catch errors early:

```
execute_shell("bun run typecheck")
```

If fails, fix action and retry before moving on.

NEVER:
- Forget `'use server'` directive at file top
- Skip Zod validation on form data
- Return raw errors to client (security risk)
- Forget `revalidatePath` after mutations

**IMPORTANT**: Server Actions are type-safe end-to-end. The client receives the exact ActionResult type you define.
