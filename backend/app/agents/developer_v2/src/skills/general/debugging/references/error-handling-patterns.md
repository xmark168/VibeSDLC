# Error Handling Patterns

## Toast Notifications (sonner)

```tsx
import { toast } from 'sonner';

toast.success('User created successfully');
toast.error('Failed to create user');
toast.error('Operation failed', { description: 'Please try again' });

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
const [state, action, pending] = useActionState(createUser, null);

<form action={action}>
  <Input name="email" />
  {state?.fieldErrors?.email && (
    <p className="text-sm text-destructive">{state.fieldErrors.email[0]}</p>
  )}
  {state?.error && <p className="text-sm text-destructive">{state.error}</p>}
</form>
```

### With react-hook-form
```tsx
const { register, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
});

<Input {...register('email')} />
{errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
```

## API Error Handling

### Client-side
```tsx
const response = await fetch('/api/users', { method: 'POST', body: JSON.stringify(data) });
if (!response.ok) {
  const error = await response.json();
  toast.error(error.message || 'Something went wrong');
  return;
}
```

### Server Action
```typescript
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
```

## Error Boundaries (error.tsx)

```tsx
// app/dashboard/error.tsx
'use client';

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 p-8">
      <h2>Something went wrong!</h2>
      <p>{error.message}</p>
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
