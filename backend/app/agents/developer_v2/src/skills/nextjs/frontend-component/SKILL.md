---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. ALWAYS activate with frontend-design together.
---

## ⚠️ CRITICAL RULES

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

### 2. Props Check - ALWAYS read component file first
```tsx
// ❌ ERROR
<BookCard id={book.id} title={book.title} />

// Component expects: interface BookCardProps { book: Book; }
// ✅ CORRECT
<BookCard book={book} />
```

### 3. Layout - NO header in pages
Root `layout.tsx` has `<Navigation />`. Pages only have content:
```tsx
// ✅ CORRECT
export default function Page() {
  return <main className="container py-8">...</main>;
}
```

### 4. Null Safety
```tsx
// ❌ CRASHES
parts.map(p => ...)

// ✅ SAFE
(parts ?? []).map(p => ...)
data?.items?.length ?? 0

// Props default
function List({ items = [] }: Props) { ... }

// State init
const [items, setItems] = useState<Item[]>([]);
```

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
