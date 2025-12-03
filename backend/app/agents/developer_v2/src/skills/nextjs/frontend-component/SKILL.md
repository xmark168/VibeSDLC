---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. Handles 'use client' directive decisions.
---

This skill guides creation of React components in Next.js 16 with React 19. Components follow the App Router architecture with Server Components as default and Client Components for interactivity.

The user needs to build pages, UI components, forms, or interactive elements.

## Before You Start

Always activate the design skill alongside this one for UI work:

```
activate_skills(["frontend-component", "frontend-design"])
```

**CRITICAL**: Before importing any custom component from `@/components/*`, you MUST read that file first to check its Props interface. Never guess prop names.

## Server vs Client Components

- **Server Components** (default): Fetch data, access database, async/await
- **Client Components** (`'use client'`): Hooks, events, browser APIs

Add `'use client'` when using:
- `useState`, `useEffect`, `useRef`, `useContext`
- `useActionState`, `useTransition`
- `onClick`, `onChange`, `onSubmit` handlers
- `useRouter`, `usePathname` from next/navigation

## Defensive Prop Handling

**CRITICAL**: Always handle undefined/null props to prevent runtime crashes.

- **Array props**: Always use default `= []`
- **Object props**: Check before accessing properties
- **Nested access**: Use optional chaining `?.`
- **Early return**: Handle loading/empty states first

```tsx
// Array props - always default to empty array
function List({ items = [] }: Props) {
  if (!items.length) return <EmptyState />;
  return items.map(item => <Item key={item.id} {...item} />);
}

// Object props - check before render
function Detail({ data }: Props) {
  if (!data) return null;
  return <div>{data.name}</div>;
}

// Nested access - use optional chaining
function Info({ user }: Props) {
  return <span>{user?.profile?.avatar ?? '/default.png'}</span>;
}
```

## Reading Components Before Import

When importing from `@/components/*`, always read the file first:

```
WRONG: write_file with <Card searchQuery={...} /> (guessing props)
CORRECT: read_file first, see Props interface, then write_file
```

Check interface format for prop passing:
- Individual props: `{ id, name }` -> pass each or spread
- Object prop: `{ item: Item }` -> pass whole object

## Page Components

Pages use `export default` and can be async:

```tsx
// app/users/[id]/page.tsx
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function UserPage({ params }: PageProps) {
  const { id } = await params;  // MUST await in Next.js 16
  const user = await prisma.user.findUnique({ where: { id } });
  
  if (!user) notFound();
  return <UserProfile user={user} />;
}
```

## Forms with useActionState

Connect forms to Server Actions:

```tsx
'use client';
import { useActionState } from 'react';
import { createItem } from '@/app/actions/item';

export function CreateForm() {
  const [state, action, pending] = useActionState(createItem, null);
  
  return (
    <form action={action}>
      <input name="name" disabled={pending} />
      {state?.fieldErrors?.name && (
        <p className="text-destructive">{state.fieldErrors.name[0]}</p>
      )}
      <button disabled={pending}>
        {pending ? 'Saving...' : 'Save'}
      </button>
      {state?.error && <p className="text-destructive">{state.error}</p>}
    </form>
  );
}
```

## API Response Handling

API routes wrap data with `successResponse()`. Always extract `.data`:

```typescript
const res = await fetch('/api/items');
const json = await res.json();
setItems(json.data ?? []);  // Extract .data, default to []
```

Always initialize useState with proper defaults:
- Arrays: `useState<Item[]>([])`
- Objects: `useState<Item | null>(null)`
- Strings: `useState('')`

## Error Handling for Users

**CRITICAL**: Never silently fail. Always show user-facing error messages.

```tsx
'use client';
import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function DataList() {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const res = await fetch('/api/items');
      if (!res.ok) throw new Error('Failed to fetch items');
      
      const json = await res.json();
      setItems(json.data ?? []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred';
      setError(message);
      // Optional: toast for non-blocking errors
      // toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {/* rest of component */}
    </div>
  );
}
```

**Rules:**
- Add `error` state alongside data state
- Show Alert/Banner for blocking errors
- Use toast (sonner) for non-blocking errors
- Clear error before new request: `setError(null)`

## Component Export Rules

- **Pages/Layouts**: `export default`
- **All other components**: Named exports only

NEVER:
- Use `'use client'` when not needed
- Guess prop names without reading component file
- Forget to `await params` in dynamic routes
- Access array/object props without defensive checks
- Pass raw API response to useState (extract .data first)
- Use default exports for non-page components

**IMPORTANT**: The directive `'use client'` must be the very first line, before any imports.
