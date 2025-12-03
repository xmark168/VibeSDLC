---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. Handles 'use client' directive decisions.
---

# Frontend Component (Next.js 16 + React 19)

## ⚠️ ALWAYS Activate Design Skill

**Before creating any UI component, MUST also activate:**
```
activate_skills(["frontend-component", "frontend-design"])
```

This ensures components follow design best practices and avoid generic AI aesthetics.

## Critical Rules

1. **Named exports ONLY** - NO default exports (except pages/layouts)
2. **'use client'** - Required ONLY for hooks, events, browser APIs
3. **Server Components** - Default, no directive needed
4. **Async params** - Always `await params` in pages
5. **shadcn/ui** - Use components from `@/components/ui/`
6. **Read before import** - MUST read custom component files before using

## ⚠️ CRITICAL: Before Importing Components

**MUST read file before importing custom components:**

| Importing From | Action |
|----------------|--------|
| `@/components/*` | READ the file first to check Props |
| `@/components/ui/*` | OK - shadcn props are standard |

### Example Flow

```
Task: "Create page with SearchResults"

WRONG ❌
→ write_file("page.tsx") with <SearchResults searchQuery={...} />
→ Type error! searchQuery doesn't exist

CORRECT ✅
→ read_file("src/components/Search/SearchResults.tsx")
→ See: interface Props { results: Item[]; onSelect: (id: string) => void }
→ write_file("page.tsx") with <SearchResults results={data} onSelect={handleSelect} />
```

### Quick Check

Before writing `<ComponentName prop={value} />`:
1. Is it from `@/components/` (not ui)? → READ IT FIRST
2. Check the `interface Props` or function params
3. Use EXACT prop names from the interface

### Props Passing Patterns

After reading component, check interface format:

```typescript
// Interface với INDIVIDUAL props
interface Props {
  id: string;
  name: string;
  price: number;
}
// → Pass: <Card id={item.id} name={item.name} price={item.price} />
// → Or spread: <Card {...item} />

// Interface với OBJECT prop
interface Props {
  textbook: Textbook;
}
// → Pass: <Card textbook={item} />
```

### Common Mistake

```tsx
// Component expects individual props
interface CardProps { id: string; name: string; }

// ❌ WRONG - passing object
<Card textbook={item} />

// ✅ CORRECT - spread or individual
<Card {...item} />
<Card id={item.id} name={item.name} />
```

## Pre-Code Checklist (MANDATORY)

⚠️ **Before writing/modifying ANY component:**

1. **Check if file uses hooks** → If YES, ensure `'use client'` is at line 1
2. **Adding hooks to existing file** → Check if `'use client'` exists, add if missing

| Import/Usage | Action Required |
|--------------|-----------------|
| `useState`, `useEffect`, `useRef` | Add `'use client'` |
| `useActionState`, `useTransition` | Add `'use client'` |
| `onClick`, `onChange`, `onSubmit` | Add `'use client'` |
| `useRouter` (next/navigation) | Add `'use client'` |

```tsx
// ⚠️ WRONG - Missing directive with hook
import { useActionState } from 'react';
export function Form() { ... }

// ✅ CORRECT - Directive at first line
'use client';
import { useActionState } from 'react';
export function Form() { ... }
```

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

## API Response Handling (IMPORTANT)

### Standard Response Format

API routes in this project use `successResponse()` which **always wraps data**:

```typescript
// API ALWAYS returns this format:
{ success: true, data: T }

// NOT raw array like:
[item1, item2, ...]
```

### Fetching Pattern

```typescript
// ✅ CORRECT - extract .data
const res = await fetch('/api/textbooks');
const json = await res.json();
setTextbooks(json.data ?? []);

// ❌ WRONG - passing raw response
const json = await res.json();
setTextbooks(json);  // json is {success, data}, not array!
```

### useState Default

```typescript
const [items, setItems] = useState<Item[]>([]);  // ✅ empty array default
```

## References

- `references/forms.md` - Form patterns with validation
- `references/shadcn-patterns.md` - shadcn/ui component examples
- `references/animations.md` - Framer Motion animation patterns
