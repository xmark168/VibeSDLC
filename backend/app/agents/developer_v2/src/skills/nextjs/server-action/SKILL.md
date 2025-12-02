---
name: server-action
description: Create Next.js 16 Server Actions. Use when building form handlers, mutations with Zod validation, or data operations that need useActionState and revalidatePath.
---

# Server Action (Next.js 16 + React 19)

## Critical Rules

1. **'use server'** - Required at top of file
2. **File location** - Put in `app/actions/` directory
3. **Zod validation** - Always validate FormData
4. **Return ActionResult** - Consistent return type
5. **revalidatePath** - Call after mutations

## Quick Reference

### ActionResult Type
```typescript
type ActionResult<T = void> = 
  | { success: true; data?: T }
  | { success: false; error: string; fieldErrors?: Record<string, string[]> };
```

### Basic Action
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

### Form with useActionState
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
      <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
    </form>
  );
}
```

### Delete with useTransition
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

## References

- `action-patterns.md` - Advanced patterns, redirect, inline actions
