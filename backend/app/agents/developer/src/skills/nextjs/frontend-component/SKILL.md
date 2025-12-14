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
- **INVENTING props that don't exist** - component may self-fetch data internally!

**Example - Component self-fetches data:**
```tsx
// FilterPanel.tsx - self-fetches authors/categories internally
interface FilterPanelProps {
  selectedAuthors: string[];     // Only IDs!
  onAuthorToggle: (id: string) => void;
  // NO 'authors' prop - component fetches itself!
}

// ❌ WRONG - passing data that component fetches itself
<FilterPanel 
  authors={authorsList}     // ERROR! Prop doesn't exist!
  selectedAuthors={selected}
/>

// ✅ CORRECT - only pass props defined in interface
<FilterPanel 
  selectedAuthors={selected}
  onAuthorToggle={handleToggle}
/>
```

**RULE: If prop doesn't exist in interface, DON'T pass it!**

**TypeScript error patterns:**
- `TS2741: Property 'X' is missing` → Add the required prop
- `TS2353: 'X' does not exist` → **REMOVE the prop - it's not in interface!**
- `TS2322: Type 'X' is not assignable` → Check if server action includes relations

## ⚠️ Data Fetching - Self-Fetch Pattern

**CRITICAL: API Route First!**
Before creating ANY component that fetches data, you MUST:
1. **Check if API route exists** - look at `src/app/api/` folder
2. **Create API route FIRST** if it doesn't exist
3. **Then create the component** that calls the API

```
❌ WRONG ORDER:
1. Create RelatedCategories.tsx (calls /api/categories/related)
2. Forget to create /api/categories/related/route.ts
→ Component breaks with 404!

✅ CORRECT ORDER:
1. Create /api/categories/related/route.ts FIRST
2. Then create RelatedCategories.tsx that calls it
```

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
        if (data.success) {
          // Handle both formats: data.data as array OR data.data.results
          const items = Array.isArray(data.data) ? data.data : (data.data?.results ?? []);
          setBooks(items);
        } else {
          setError(data.error);
        }
      })
      .catch(() => setError('Failed to load'))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <Skeleton />;
  if (error) return <Alert>{error}</Alert>;
  return <BookGrid books={books} />;
}

// API Response Formats:
// - Standard: { success: true, data: [...] } → use data.data
// - With results: { success: true, data: { results: [...] } } → use data.data.results
// - Always safe: Array.isArray(data.data) ? data.data : (data.data?.results ?? [])
```

**Rules:**
- Define interface locally with ONLY fields you need for display
- Use `useState` for data, loading, error states
- Fetch from API route in `useEffect`
- Handle loading/error states properly

**NEVER** receive fetched data as props from parent page - always self-fetch!

---

## More Rules

### 1. 'use client' - CRITICAL SYNTAX RULES

**'use client' MUST be FIRST LINE of file, NEVER inside function!**

```tsx
// ❌ WRONG - 'use client' inside function body
function MyComponent() {
  'use client';  // ERROR: Invalid position!
  const router = useRouter();
}

// ❌ WRONG - using require() instead of import
function MyComponent() {
  const { useRouter } = require('next/navigation');  // ERROR!
}

// ❌ WRONG - 'use client' after imports
import { useState } from 'react';
'use client';  // ERROR: Must be first line!

// ✅ CORRECT - 'use client' at FIRST LINE, use import
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function BookCard() {
  const router = useRouter();
  const [liked, setLiked] = useState(false);
  return <button onClick={() => setLiked(true)}>Like</button>;
}
```

**When to add 'use client':**
- useState, useEffect, useRef, useContext
- onClick, onChange, onSubmit, onHover
- useRouter, usePathname, useSearchParams

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

### 4. Type Casting - Filter/Toggle Functions ⚠️

Filter values from UI components are often union types:

```tsx
interface ActiveFilter {
  type: 'category' | 'author' | 'rating';
  value: string | number | boolean;  // Union type!
}

// ❌ WRONG - TypeScript error: Type 'string | number | boolean' not assignable to 'string'
const handleRemoveFilter = (filter: ActiveFilter) => {
  switch (filter.type) {
    case 'category':
      toggleCategory(filter.value);  // Error!
      break;
  }
};

// ✅ CORRECT - Cast to expected type
const handleRemoveFilter = (filter: ActiveFilter) => {
  switch (filter.type) {
    case 'category':
      toggleCategory(filter.value as string);  // OK
      break;
    case 'rating':
      setMinRating(filter.value as number);  // OK
      break;
  }
};

// ✅ ALSO CORRECT - Use String() for string conversion
toggleCategory(String(filter.value));
```

**RULE:** When filter.value/item.value has union type, cast before passing to typed functions

### 5. Route Navigation - USE EXACT PATHS
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

## Filter State Pattern - URL Sync

When building filter/search pages, sync state with URL:

```typescript
'use client';
import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, useCallback } from 'react';

export function SearchPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState('relevance');

  // Initialize filters from URL on mount (empty deps = run once)
  useEffect(() => {
    const categories = searchParams.get('categories')?.split(',').filter(Boolean) ?? [];
    const sort = searchParams.get('sort') ?? 'relevance';
    setSelectedCategories(categories);
    setSortBy(sort);
  }, []);  // Empty deps - only run once on mount!

  // Update URL when filters change
  const updateURL = useCallback((filters: FilterState) => {
    const params = new URLSearchParams();
    if (filters.query) params.set('q', filters.query);
    if (filters.categories.length > 0) {
      params.set('categories', filters.categories.join(','));  // comma-separated!
    }
    if (filters.sort !== 'relevance') {
      params.set('sort', filters.sort);  // NOT 'sortBy'!
    }
    router.push(`/search?${params.toString()}`, { scroll: false });
  }, [router]);

  // Fetch data with current filters
  useEffect(() => {
    const params = new URLSearchParams();
    params.set('q', query);
    if (selectedCategories.length > 0) {
      params.set('categories', selectedCategories.join(','));
    }
    if (sortBy !== 'relevance') params.set('sort', sortBy);
    
    fetch(`/api/books/search?${params.toString()}`)
      .then(res => res.json())
      .then(data => setBooks(data.data ?? []));
  }, [query, selectedCategories, sortBy]);
}
```

**Param naming MUST match API route:**
- Frontend sends `categories` → API reads `searchParams.get('categories')`
- Frontend sends `sort` → API reads `searchParams.get('sort')`
- **NEVER** use `categoryId`, `authorId`, `sortBy`

## NEVER
- `'use client'` when not needed
- Guess props without reading component
- Forget `await params` in dynamic routes
- Access array/object without null checks
- Add Header in pages (already in layout)
- Import from `'./badge'` - use `'@/components/ui/badge'`
- Create UI components that already exist in shadcn/ui
- Use `sortBy` param - always use `sort`
- Use `categoryId`/`authorId` for multi-select - use `categories`/`authors`
