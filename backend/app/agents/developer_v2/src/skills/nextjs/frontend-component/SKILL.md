---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. ALWAYS activate with frontend-design together.
---

## ⚠️ CRITICAL RULES

### 1. Props Check - ALWAYS read component file first
```tsx
// ❌ ERROR
<BookCard id={book.id} title={book.title} />

// Component expects: interface BookCardProps { book: Book; }
// ✅ CORRECT
<BookCard book={book} />
```

### 2. Layout - NO header in pages
Root `layout.tsx` has `<Navigation />`. Pages only have content:
```tsx
// ✅ CORRECT
export default function Page() {
  return <main className="container py-8">...</main>;
}
```

### 3. Null Safety
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

## Server vs Client

- **Server** (default): async/await, no hooks
- **Client** (`'use client'`): useState, useEffect, onClick

`'use client'` MUST be first line.

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
