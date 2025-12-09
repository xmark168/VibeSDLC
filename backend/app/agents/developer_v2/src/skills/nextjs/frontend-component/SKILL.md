---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. ALWAYS activate with frontend-design together.
---

## ⚠️ IMPORT PATHS - USE EXACT PATHS

**Component imports MUST match exact file location:**

```tsx
// File at: src/components/search/SearchBar.tsx
// ✅ CORRECT
import { SearchBar } from '@/components/search/SearchBar';

// ❌ WRONG - path doesn't match file location
import { SearchBar } from '@/components/SearchBar';
```

**Rules:**
- Check "Component Imports" section in context for exact paths
- Path must match file location: `src/components/[folder]/[Name].tsx` → `@/components/[folder]/[Name]`
- Never guess import paths - use paths from context

## ⚠️ PROPS MATCHING - MOST CRITICAL

**Before using ANY component, you MUST:**
1. READ the component file first
2. Find `interface XxxProps { ... }`
3. Pass props EXACTLY as defined

```tsx
// Component file defines:
interface BookCardProps {
  book: Book;  // Expects OBJECT, not individual fields!
}

// ❌ WRONG - passing individual fields
<BookCard id={book.id} title={book.title} author={book.author} />

// ✅ CORRECT - pass the object
<BookCard book={book} />
```

**Common mistakes:**
- Passing `{ name, slug, count }` when component expects `{ category: Category }`
- Passing individual fields when component expects an object prop
- Not reading the Props interface before using component
- Missing required props: `<Banner />` instead of `<Banner title="Sale" />`

**TypeScript error patterns:**
- `TS2741: Property 'X' is missing` → Add the required prop
- `TS2353: 'X' does not exist` → Remove invented prop, check interface
- `TS2322: Type 'X' is not assignable` → Check if server action includes relations

## ⚠️ Data Fetching - Self-Fetch Pattern

Components that need data should SELF-FETCH from API routes:

```tsx
'use client';
import { useEffect, useState } from 'react';

interface Book {
  id: string;
  title: string;
  price: number;
}

export function FeaturedBooks() {
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/books/featured')
      .then(res => res.json())
      .then(data => {
        if (data.success) setBooks(data.data ?? []);
        else setError(data.error);
      })
      .catch(() => setError('Failed to load'))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <Skeleton />;
  if (error) return <Alert>{error}</Alert>;
  return <BookGrid books={books} />;
}
```

**Rules:**
- Define interface locally with ONLY fields you need for display
- Use `useState` for data, loading, error states
- Fetch from API route in `useEffect`
- Handle loading/error states properly

**NEVER** receive fetched data as props from parent page - always self-fetch!

---

## More Rules

### 1. 'use client' - ADD when using hooks/events
```tsx
// MUST add 'use client' as FIRST LINE when component has:
// - useState, useEffect, useRef, useContext
// - onClick, onChange, onSubmit, onHover
// - useRouter, usePathname

'use client';  // ← FIRST LINE, before imports!

import { useState } from 'react';

export function BookCard() {
  const [liked, setLiked] = useState(false);
  return <button onClick={() => setLiked(true)}>Like</button>;
}
```

### 2. Layout - NO header in pages
Root `layout.tsx` has `<Navigation />`. Pages only have content:
```tsx
// ✅ CORRECT
export default function Page() {
  return <main className="container mx-auto px-4 py-8">...</main>;
}
```

### 2.1 Container & Text Centering
```tsx
// ❌ WRONG - container not centered
<div className="container">

// ✅ CORRECT - always add mx-auto + px-4
<div className="container mx-auto px-4">

// ❌ WRONG - text not centered  
<div>
  <span className="inline-block">Title</span>
</div>

// ✅ CORRECT - parent text-center + child block
<div className="text-center">
  <span className="block">Title</span>
  <h2>Heading</h2>
  <p className="mx-auto max-w-2xl">Description</p>
</div>
```

**RULES:**
- `container` MUST have `mx-auto px-4`
- Centered text sections: parent `text-center`, children `block` (not inline-block)
- Long text: add `mx-auto max-w-2xl` to constrain width

### 3. Null Safety - CRITICAL ⚠️
API responses may have undefined nested arrays/objects!

```tsx
// ❌ CRASHES at runtime (category.books could be undefined)
category.books.filter(b => b.coverImage)
data.items.map(item => ...)

// ✅ ALWAYS defensive - use ?? [] or ?.
(category.books ?? []).filter(b => b.coverImage)
(data?.items ?? []).map(item => ...)
data?.items?.length ?? 0

// Props default
function List({ items = [] }: Props) { ... }
```

**RULE:** Any `.map()`, `.filter()`, `.slice()` on API/fetched data MUST have `?? []` or optional chaining

```tsx
// State init - always default to empty array
const [items, setItems] = useState<Item[]>([]);
```

### 4. Route Navigation - USE EXACT PATHS
Check the plan/context for existing page routes before using `router.push()` or `<Link>`:

```tsx
// ❌ WRONG - guessing route that doesn't exist
router.push(`/books?search=${query}`);  // 404 if /books/page.tsx doesn't exist!

// ✅ CORRECT - use route from plan
router.push(`/search?q=${query}`);  // /search/page.tsx exists in plan
```

**RULE:** Always check Dependencies section for existing page paths before navigation.

## Page with Dynamic Params

```tsx
interface PageProps { params: Promise<{ id: string }>; }

export default async function Page({ params }: PageProps) {
  const { id } = await params;  // MUST await in Next.js 16
  const data = await prisma.item.findUnique({ where: { id } });
  if (!data) notFound();
  return <Detail data={data} />;
}
```

## Forms with useActionState

```tsx
'use client';
const [state, action, pending] = useActionState(serverAction, null);

<form action={action}>
  <input name="field" disabled={pending} />
  {state?.fieldErrors?.field && <p className="text-destructive">{state.fieldErrors.field[0]}</p>}
  <button disabled={pending}>{pending ? '...' : 'Submit'}</button>
</form>
```

## shadcn/ui Components

All UI components are at `@/components/ui/*`:
```tsx
// ✅ CORRECT
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

// ❌ WRONG - file doesn't exist!
import { Badge } from './badge';
```

## Data Fetching

```tsx
const [items, setItems] = useState<Item[]>([]);
const [error, setError] = useState<string | null>(null);

const res = await fetch('/api/items');
if (!res.ok) { setError('Failed to fetch'); return; }
setItems((await res.json()).data ?? []);

// Show error
{error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
```

## NEVER
- `'use client'` when not needed
- Guess props without reading component
- Forget `await params` in dynamic routes
- Access array/object without null checks
- Add Header in pages (already in layout)
- Import from `'./badge'` - use `'@/components/ui/badge'`
- Create UI components that already exist in shadcn/ui
