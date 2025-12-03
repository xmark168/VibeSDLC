---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. Handles 'use client' directive decisions.
---

This skill guides creation of React components in Next.js 16 with React 19.

The user needs to build pages, UI components, forms, or interactive elements using the App Router architecture.

## Before You Start

Always activate the design skill alongside this one for UI work:

```
activate_skills(["frontend-component", "frontend-design"])
```

**CRITICAL**: Before importing any custom component from `@/components/*`, you MUST read that file first to check its Props interface. Never guess prop names.

## Server vs Client Components

Next.js components are Server Components by default. Add `'use client'` only when needed:

- **Server Components** (default, no directive): Can fetch data, access database, use async/await
- **Client Components** (`'use client'`): Can use hooks, handle events, access browser APIs

Add `'use client'` when using:
- `useState`, `useEffect`, `useRef`, `useContext`
- `useActionState`, `useTransition`
- `onClick`, `onChange`, `onSubmit` handlers
- `useRouter`, `usePathname` from next/navigation

## Reading Components Before Import

When importing from `@/components/*` (not ui), always read the file first:

```
Task: Create page with SearchResults

WRONG:
-> write_file("page.tsx") with <SearchResults searchQuery={...} />
-> Type error! searchQuery prop doesn't exist

CORRECT:
-> read_file("src/components/Search/SearchResults.tsx")
-> See: interface Props { results: Item[]; onSelect: (id: string) => void }
-> write_file("page.tsx") with <SearchResults results={data} onSelect={handleSelect} />
```

Check the interface format to know how to pass props:

```typescript
// Individual props - pass each one or spread
interface Props { id: string; name: string; }
// Use: <Card id={item.id} name={item.name} /> or <Card {...item} />

// Object prop - pass the whole object
interface Props { textbook: Textbook; }
// Use: <Card textbook={item} />
```

## Page Components

Pages use `export default` and can be async for data fetching:

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

## Server Components

Use for data fetching and rendering:

```tsx
// No directive needed - server by default
export async function UserList({ limit = 10 }) {
  const users = await prisma.user.findMany({ take: limit });
  
  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
}
```

## Client Components

Use for interactivity:

```tsx
'use client';
import { useState } from 'react';

export function Counter() {
  const [count, setCount] = useState(0);
  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  );
}
```

## Forms with useActionState

Connect forms to Server Actions:

```tsx
'use client';
import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';

export function CreateUserForm() {
  const [state, action, pending] = useActionState(createUser, null);
  
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
// CORRECT - extract .data from response
const res = await fetch('/api/items');
const json = await res.json();
setItems(json.data ?? []);

// WRONG - json is {success, data}, not the array
setItems(json);
```

Always initialize useState with empty array for lists:

```typescript
const [items, setItems] = useState<Item[]>([]);
```

## Component Export Rules

- **Pages/Layouts**: Use `export default`
- **All other components**: Use named exports only

```tsx
// Page - default export
export default function Page() { ... }

// Component - named export
export function UserCard({ user }: Props) { ... }
```

NEVER:
- Use `'use client'` in Server Components that don't need it
- Guess prop names without reading the component file
- Forget to `await params` in dynamic route pages
- Use default exports for non-page components
- Pass raw API response to useState (extract .data first)

**IMPORTANT**: The directive `'use client'` must be the very first line of the file, before any imports.
