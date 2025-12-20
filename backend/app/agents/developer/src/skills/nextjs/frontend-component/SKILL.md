---
name: frontend-component
description: Create React/Next.js 16 components. Use when building pages, client/server components, forms with useActionState, or UI with shadcn/ui. ALWAYS activate with frontend-design together.
---

## ⚠️ IMPORT PATHS - USE EXACT PATHS

**Component imports MUST match exact file location:**

```tsx
// File at: src/components/search/SearchBar.tsx
//  CORRECT
import { SearchBar } from '@/components/search/SearchBar';

// WRONG - path doesn't match file location
import { SearchBar } from '@/components/SearchBar';
```

**Rules:**
- Check "Component Imports" section in plan context for exact paths
  - This section appears after file tree, shows: `ComponentName → import path`
  - Example: `SearchBar → import { SearchBar } from '@/components/search/SearchBar'`
- Path must match file location: `src/components/[folder]/[Name].tsx` → `@/components/[folder]/[Name]`
- Never guess import paths - always use exact paths from "Component Imports" section

## ⚠️ PROPS MATCHING - MOST CRITICAL

**🚨 MANDATORY WORKFLOW - DO NOT SKIP:**

**Step 1: ALWAYS read the component file from Pre-loaded Code or Dependencies**
```typescript
// BEFORE using <CategoryNavigation mobile={true} onCategoryClick={...} />
// YOU MUST find CategoryNavigation.tsx and read its Props interface!

// Example: Found in Pre-loaded Code:
interface CategoriesDropdownProps {
  mobile?: boolean;
  onCategoryClick?: () => void;
}

// Now you know EXACTLY what props to pass
<CategoriesDropdown mobile={true} onCategoryClick={handleClick} />
```

**Step 2: Pass ONLY props that exist in the interface**
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

**Step 3: If component NOT in Pre-loaded Code → DON'T use it!**
```tsx
// ❌ WRONG - guessing props for component you haven't read
<CategoryNavigation mobile={true} onCategoryClick={...} />
// What if CategoryNavigation doesn't accept these props?

// ✅ CORRECT - only use components you've verified in Pre-loaded Code
// Or use built-in shadcn components instead!
```

**TypeScript error TS2322 means WRONG PROPS!**
```
error TS2322: Type '{ mobile: boolean; onCategoryClick: () => void; }' 
is not assignable to type 'IntrinsicAttributes'.
Property 'mobile' does not exist on type 'IntrinsicAttributes'.
```

**This error means:**
1. Component doesn't accept `mobile` prop
2. You're passing props that don't exist in Props interface
3. **You FORGOT to read the component file first!**

**Common mistakes:**
- **NOT reading Props interface before using component** ← #1 cause of errors!
- Passing `{ name, slug, count }` when component expects `{ category: Category }`
- Passing individual fields when component expects an object prop
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

// WRONG - passing data that component fetches itself
<FilterPanel 
  authors={authorsList}     // ERROR! Prop doesn't exist!
  selectedAuthors={selected}
/>

//  CORRECT - only pass props defined in interface
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

## ⚠️ Using Zustand Stores - CRITICAL

**BEFORE using any store hook (`useXxxStore()`), CHECK the store file in Pre-loaded Code!**

```typescript
// ❌ WRONG - assuming store interface without checking
const { paymentMethod, bankDetails, orderCode } = usePaymentStore();
// What if PaymentState doesn't have bankDetails or orderCode?

// ✅ CORRECT - check Pre-loaded Code first
// 1. Find src/lib/payment-store.ts in Pre-loaded Code section
// 2. Read PaymentState interface to see available fields
// 3. ONLY destructure fields that EXIST in the interface

// Example: If PaymentState only has { paymentMethod, setPaymentMethod }
const { paymentMethod, setPaymentMethod } = usePaymentStore();  // Only use what exists!
```

**Common store files and locations:**
- Payment: `src/lib/payment-store.ts` → `usePaymentStore()`
- Cart: `src/lib/cart-store.ts` → `useCartStore()`
- Auth: `src/lib/auth-store.ts` → `useAuthStore()` (if exists)

**Rules:**
1. **Always check store file BEFORE using the hook**
2. **Only destructure fields that exist** in the interface
3. **If store file is NOT in Pre-loaded Code**:
   - Use minimal assumptions (only `paymentMethod` for payment, only `items` for cart)
   - Or request the store file as a dependency
4. **Never invent store fields** - read the actual interface!

**Example - Reading store interface:**
```typescript
// In Pre-loaded Code: src/lib/cart-store.ts
interface CartState {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  // NO 'total' or 'count' fields!
}

// ✅ CORRECT - only use what exists
const { items, addItem, removeItem } = useCartStore();
const total = items.reduce((sum, item) => sum + item.price, 0);  // Calculate yourself

// ❌ WRONG - assuming fields that don't exist
const { items, total, count } = useCartStore();  // TS ERROR!
```

**Why this matters:**
- TypeScript will error on non-existent fields: `Property 'X' does not exist on type 'YState'`
- Component will fail to compile
- Wastes time debugging obvious errors

**If you get TS error about store fields:**
1. Check Pre-loaded Code for the store file
2. Read the actual interface
3. Only use fields that are defined there

## ⚠️ Data Fetching - Self-Fetch Pattern

**CRITICAL: API Route First!**
Before creating ANY component that fetches data, you MUST:
1. **Check if API route exists** - look at `src/app/api/` folder
2. **Create API route FIRST** if it doesn't exist
3. **Then create the component** that calls the API

```
WRONG ORDER:
1. Create RelatedCategories.tsx (calls /api/categories/related)
2. Forget to create /api/categories/related/route.ts
→ Component breaks with 404!

 CORRECT ORDER:
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
// WRONG - 'use client' inside function body
function MyComponent() {
  'use client';  // ERROR: Invalid position!
  const router = useRouter();
}

// WRONG - using require() instead of import
function MyComponent() {
  const { useRouter } = require('next/navigation');  // ERROR!
}

// WRONG - 'use client' after imports
import { useState } from 'react';
'use client';  // ERROR: Must be first line!

// ✅ CORRECT - 'use client' at FIRST LINE (line 1!)
'use client';  // This MUST be the very first line

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

### 2. String Quotes - CRITICAL for JSX Text ⚠️

**RULE: Use DOUBLE QUOTES for JSX strings with apostrophes/contractions**

```tsx
// ❌ WRONG - Single quotes with apostrophe causes TypeScript error
<p>{'Thank you! We'll send you a confirmation.'}</p>
//              ^ ERROR: Unexpected token

<Alert>{"Don't worry, we've got you covered!"}</Alert>
//        ^ ERROR: String breaks at apostrophe

// ✅ CORRECT - Double quotes for outer string
<p>{"Thank you! We'll send you a confirmation."}</p>
<Alert>{"Don't worry, we've got you covered!"}</Alert>

// ✅ ALSO CORRECT - Template literals (if no variables)
<p>{`Thank you! We'll send you a confirmation.`}</p>
```

**When to use each quote style:**

| Quote Type | Use For | Example |
|------------|---------|---------|
| Double `"` | JSX text with contractions (we'll, don't, it's) | `{"We'll contact you soon"}` |
| Single `'` | Simple JSX text WITHOUT apostrophes | `{'Hello'}` or `{'Submit'}` |
| Template `` ` `` | Strings with variables or multi-line | `` {`Hello ${name}`} `` |

**Common contractions to watch for:**
- we'll, you'll, I'll, they'll
- don't, won't, can't, shouldn't
- it's, that's, here's, there's
- I've, we've, you've

**CRITICAL: JSX expression strings with apostrophes MUST use double quotes or template literals**

```tsx
// ❌ WRONG - Will break TypeScript
{showMessage 
  ? 'We'll send confirmation'  // ERROR
  : 'Don't worry'}             // ERROR

// ✅ CORRECT - Double quotes
{showMessage 
  ? "We'll send confirmation"
  : "Don't worry"}

// ✅ ALSO CORRECT - Template literals  
{showMessage 
  ? `We'll send confirmation`
  : `Don't worry`}
```

**Exception - Plain text in JSX (no braces):**
```tsx
// These are OK (React escapes apostrophes automatically)
<p>We'll send you a confirmation.</p>
<Alert>Don't worry!</Alert>
```

### 3. Type Annotations - React 19 + Next.js 16

**Use `React.ReactElement`, NOT `JSX.Element`:**

```tsx
// ❌ WRONG - JSX namespace not available with new JSX transform
const renderStars = (rating: number): JSX.Element[] => {
  return Array.from({ length: 5 }, (_, i) => <Star key={i} />);
};

// ✅ CORRECT - Use React.ReactElement
const renderStars = (rating: number): React.ReactElement[] => {
  return Array.from({ length: 5 }, (_, i) => <Star key={i} />);
};

// ✅ ALSO CORRECT - Let TypeScript infer (simplest)
const renderStars = (rating: number) => {
  return Array.from({ length: 5 }, (_, i) => <Star key={i} />);
};
```

**Rules:**
- With React 19 + Next.js 16 (`jsx: "react-jsx"`), use `React.ReactElement` for JSX type annotations
- `JSX.Element` requires separate import and is deprecated pattern
- Best practice: Let TypeScript infer return types when obvious
- For function params expecting JSX: use `React.ReactNode` or `React.ReactElement`

**Common patterns:**
```tsx
// Function returning single element
const Header = (): React.ReactElement => <h1>Title</h1>;

// Function returning array of elements  
const renderItems = (items: Item[]): React.ReactElement[] => 
  items.map(item => <div key={item.id}>{item.name}</div>);

// Component prop accepting JSX
interface Props {
  icon: React.ReactElement;  // Single element
  children: React.ReactNode; // Any renderable content
}
```

**TypeScript config context:**
```json
{
  "compilerOptions": {
    "jsx": "react-jsx",  // New transform - JSX namespace not auto-available
  }
}
```

### 4. Event Handler Errors - Server vs Client Components

**Error:** "Event handlers cannot be passed to Client Component props"

**Cause:** You're passing a function from Server Component to Client Component.

```tsx
// ❌ PROBLEM - Server Component passing handler to Client Component
// page.tsx (Server Component by default - no 'use client')
export default function Page() {
  const handleSort = (sort: string) => { ... };  // Function in Server Component
  
  return <KanbanBoard onSortChange={handleSort} />;  // ❌ Passing to Client Component
}

// kanban-board.tsx
'use client';
export function KanbanBoard({ onSortChange }: { onSortChange: (sort: string) => void }) {
  return <button onClick={() => onSortChange('date')}>Sort</button>;
}
```

**Solution A - Convert parent to Client Component (Simple):**

Use this when the page doesn't need server-side data fetching or server actions.

```tsx
// page.tsx - Add 'use client' to make it a Client Component
'use client';  // ← Add this at first line!

export default function Page() {
  const handleSort = (sort: string) => { ... };  // ✅ Now OK - function in Client Component
  return <KanbanBoard onSortChange={handleSort} />;  // ✅ Can pass handlers
}

// kanban-board.tsx - No changes needed
'use client';
export function KanbanBoard({ onSortChange }: { onSortChange: (sort: string) => void }) {
  return <button onClick={() => onSortChange('date')}>Sort</button>;
}
```

**Solution B - Move logic down (Better for SEO/SSR):**

Use this when you need server-side data fetching (`async` component) or server actions.

```tsx
// page.tsx - Keep as Server Component
export default async function Page() {
  const data = await fetchData();  // Server-side data fetching preserved
  return <KanbanBoard initialData={data} />;  // Pass data, not handlers
}

// kanban-board.tsx - Handle state + events internally
'use client';

export function KanbanBoard({ initialData }: { initialData: Data[] }) {
  const [sort, setSort] = useState('date');
  const [data, setData] = useState(initialData);
  
  const handleSort = (newSort: string) => {  // ✅ Handler in Client Component
    setSort(newSort);
    // Sort logic here
  };
  
  return <button onClick={() => handleSort('date')}>Sort</button>;
}
```

**When to use which:**
- **Solution A (Add 'use client' to parent)**: Simple pages with no server data fetching, no form actions
- **Solution B (Move handler to child)**: Pages with `async` data fetching, forms with server actions, or when you want to preserve SSR benefits

**CRITICAL RULES:**
- ✅ **DO** add `'use client'` to parent if it's a simple page
- ✅ **DO** move handler logic into child component if parent needs to stay server component
- ❌ **NEVER** remove `'use client'` from child components that use hooks/events
- ❌ **NEVER** try to pass functions from Server Components to Client Components

### 5. Layout - NO header in pages
Root `layout.tsx` has `<Navigation />`. Pages only have content:
```tsx
//  CORRECT
export default function Page() {
  return <main className="container mx-auto px-4 py-8">...</main>;
}
```

### 5.1 Container & Text Centering
```tsx
// WRONG - container not centered
<div className="container">

//  CORRECT - always add mx-auto + px-4
<div className="container mx-auto px-4">

// WRONG - text not centered  
<div>
  <span className="inline-block">Title</span>
</div>

//  CORRECT - parent text-center + child block
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

### 6. Null Safety - CRITICAL ⚠️
API responses may have undefined nested arrays/objects!

```tsx
// CRASHES at runtime (category.books could be undefined)
category.books.filter(b => b.coverImage)
data.items.map(item => ...)

//  ALWAYS defensive - use ?? [] or ?.
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

**String Methods - ALWAYS use optional chaining:**

```tsx
// ❌ WRONG - crashes if value is null/undefined
{order.paymentMethod.replace('_', ' ')}
category.name.toLowerCase()
user.email.split('@')[0]

// ✅ CORRECT - safe with optional chaining
{order.paymentMethod?.replace('_', ' ')}
{category.name?.toLowerCase()}
{user.email?.split('@')[0]}

// ✅ CORRECT - with fallback
{order.paymentMethod?.replace('_', ' ') ?? 'N/A'}
{category.name?.toLowerCase() ?? ''}
```

**RULE:** Any string method (`.replace()`, `.toLowerCase()`, `.toUpperCase()`, `.split()`, `.trim()`, etc.) 
on object properties or API data MUST use optional chaining `?.`

**Exception:** Only skip `?.` if value is guaranteed non-null:
- Local variables: `const name = "John"; name.toLowerCase()` ✅
- Literal strings: `"hello".toUpperCase()` ✅
- Form inputs: `e.target.value.replace(...)` ✅ (guaranteed string)

### 7. Type Casting - Filter/Toggle Functions ⚠️

Filter values from UI components are often union types:

```tsx
interface ActiveFilter {
  type: 'category' | 'author' | 'rating';
  value: string | number | boolean;  // Union type!
}

// WRONG - TypeScript error: Type 'string | number | boolean' not assignable to 'string'
const handleRemoveFilter = (filter: ActiveFilter) => {
  switch (filter.type) {
    case 'category':
      toggleCategory(filter.value);  // Error!
      break;
  }
};

//  CORRECT - Cast to expected type
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

//  ALSO CORRECT - Use String() for string conversion
toggleCategory(String(filter.value));
```

**RULE:** When filter.value/item.value has union type, cast before passing to typed functions

### 8. Route Navigation - USE EXACT PATHS
Check the plan/context for existing page routes before using `router.push()` or `<Link>`:

```tsx
// ❌ WRONG - guessing route that doesn't exist
router.push(`/books?search=${query}`);  // 404 if /books/page.tsx doesn't exist!

//  CORRECT - use route from plan
router.push(`/search?q=${query}`);  // /search/page.tsx exists in plan
```

**RULES:** 
- Always check Dependencies section for existing page paths before navigation
- **Use `q` for search query parameter** (NOT `search`, `query`, or other names)
- Standard pattern: `/search?q={query}` for search pages

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
//  CORRECT
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

// WRONG - file doesn't exist!
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
