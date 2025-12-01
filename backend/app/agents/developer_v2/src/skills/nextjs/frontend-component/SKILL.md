---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client components, forms with useActionState, or UI components using shadcn/ui.
---

# Frontend Component (Next.js 16 + React 19)

## Critical Rules

1. **Named exports ONLY** - NO default exports (except pages/layouts)
2. **'use client'** - Required ONLY for hooks, events, browser APIs
3. **Server Components** - Default, no directive needed
4. **Async params** - Always `await params` in pages
5. **shadcn/ui** - Use components from `@/components/ui/`

## Quick Reference

### Page Component
```tsx
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function Page({ params }: PageProps) {
  const { id } = await params;  // MUST await
  const data = await prisma.item.findUnique({ where: { id } });
  return <div>{data.name}</div>;
}
```

### Server Component (default)
```tsx
export async function UserList({ limit = 10 }) {
  const users = await prisma.user.findMany({ take: limit });
  return <div>{users.map(u => <UserCard key={u.id} user={u} />)}</div>;
}
```

### Client Component
```tsx
'use client';
import { useState } from 'react';

export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### Form with useActionState
```tsx
'use client';
import { useActionState } from 'react';

export function CreateForm() {
  const [state, action, pending] = useActionState(createAction, null);
  return (
    <form action={action}>
      <input name="title" disabled={pending} />
      <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
      {state?.error && <p className="text-destructive">{state.error}</p>}
    </form>
  );
}
```

## When to Use 'use client'

| Need | Directive |
|------|-----------|
| useState, useEffect | 'use client' |
| onClick, onChange | 'use client' |
| useActionState | 'use client' |
| Fetch from DB | Server (no directive) |
| Access env secrets | Server (no directive) |

## References

- `forms.md` - Detailed form patterns with validation
- `shadcn-patterns.md` - shadcn/ui component examples
