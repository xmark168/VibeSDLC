---
name: error-handling
description: Handle errors with toast notifications and form feedback. Use when showing success/error messages to users.
---

# Error Handling

## Toast Notifications (sonner)

```tsx
import { toast } from 'sonner';

// Success
toast.success('User created successfully');

// Error
toast.error('Failed to create user');

// With description
toast.error('Operation failed', {
  description: 'Please try again later',
});

// Promise (loading → success/error)
toast.promise(createUser(data), {
  loading: 'Creating user...',
  success: 'User created!',
  error: 'Failed to create user',
});
```

## Form Error Display

### With useActionState
```tsx
'use client';
import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';

export function CreateUserForm() {
  const [state, action, pending] = useActionState(createUser, null);

  return (
    <form action={action} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" />
        {state?.fieldErrors?.email && (
          <p className="text-sm text-destructive mt-1">
            {state.fieldErrors.email[0]}
          </p>
        )}
      </div>

      {state?.error && (
        <p className="text-sm text-destructive">{state.error}</p>
      )}

      <Button disabled={pending}>
        {pending ? 'Creating...' : 'Create'}
      </Button>
    </form>
  );
}
```

### With react-hook-form
```tsx
'use client';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email('Invalid email'),
});

export function Form() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input {...register('email')} />
      {errors.email && (
        <p className="text-sm text-destructive">{errors.email.message}</p>
      )}
    </form>
  );
}
```

## API Error Handling

### In Client Component
```tsx
'use client';
import { toast } from 'sonner';

async function handleSubmit() {
  try {
    const response = await fetch('/api/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      toast.error(error.message || 'Something went wrong');
      return;
    }

    const result = await response.json();
    toast.success('Success!');
  } catch (error) {
    toast.error('Network error. Please try again.');
  }
}
```

### In Server Action
```typescript
'use server';

export async function createUser(
  prevState: ActionResult | null,
  formData: FormData
): Promise<ActionResult> {
  try {
    // ... validation and creation
    return { success: true };
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError) {
      if (error.code === 'P2002') {
        return { success: false, error: 'Email already exists' };
      }
    }
    return { success: false, error: 'Failed to create user' };
  }
}
```

## Error Boundaries

### Page-level (error.tsx)
```tsx
// app/dashboard/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 p-8">
      <h2 className="text-xl font-bold">Something went wrong!</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

## Quick Reference

| Scenario | Method |
|----------|--------|
| Success message | `toast.success('Done!')` |
| Error message | `toast.error('Failed')` |
| Form field error | `{errors.field && <p>...</p>}` |
| API error | `if (!response.ok) toast.error(...)` |
| Async with loading | `toast.promise(promise, {...})` |
