## Project Overview

Next.js 15 boilerplate with TypeScript, App Router, Prisma, NextAuth v5, Tailwind CSS 4, and shadcn/ui components. Uses bun as package manager.

**Key Stack:**
- Next.js 15 + React 19
- NextAuth v5 (beta) with Credentials provider + Prisma adapter
- Prisma ORM + PostgreSQL
- Tailwind CSS 4 + 50+ shadcn/ui components (Radix UI)
- React Hook Form + Zod validation
- Zustand for state management
- Jest + React Testing Library

## Common Commands

```bash
# Development
bun dev                  # Start dev server with Turbopack
bun dev:webpack          # Start dev server with Webpack (fallback)

# Build & Deploy
bun run build            # Production build
bun start                # Start production server

# Testing
bun test                 # Run all tests
bun test:watch           # Run tests in watch mode
bun test:coverage        # Run tests with coverage report

# Linting & Formatting
bun lint                 # Run ESLint
bun lint:fix             # Fix ESLint errors
bun format               # Format with Prettier

# Database (Prisma)
bunx prisma generate     # Generate Prisma Client (after schema changes)
bunx prisma db push      # Push schema changes to database (dev)
bunx prisma migrate dev  # Create and apply migrations (production-ready)
bunx prisma studio       # Open Prisma Studio GUI
```

## Next.js 15 App Router Conventions

### Special Files (MUST follow these conventions)

| File | Purpose |
|------|---------|
| `page.tsx` | Route page (makes folder publicly accessible) |
| `layout.tsx` | Shared layout (wraps children, persists across navigation) |
| `loading.tsx` | Loading UI (automatic Suspense boundary) |
| `error.tsx` | Error boundary (must be Client Component) |
| `not-found.tsx` | 404 page for route segment |
| `route.ts` | API endpoint (GET, POST, PUT, DELETE handlers) |
| `template.tsx` | Like layout but re-renders on navigation |

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Files | `kebab-case` | `user-profile.tsx`, `api-response.ts` |
| Components | `PascalCase` | `UserProfile`, `LoginForm` |
| Variables/Props | `camelCase` | `userData`, `isLoading` |
| Route folders | `lowercase` | `dashboard`, `user-settings` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_ITEMS`, `API_URL` |

### Route Groups (Organize without affecting URL)

```
src/app/
├── (auth)/                 # Group: /login, /register (no /auth prefix)
│   ├── login/
│   │   └── page.tsx        # → /login
│   └── register/
│       └── page.tsx        # → /register
├── (dashboard)/            # Group: dashboard routes
│   ├── layout.tsx          # Shared dashboard layout
│   ├── page.tsx            # → / (dashboard home)
│   └── settings/
│       └── page.tsx        # → /settings
└── api/                    # API routes
    └── users/
        └── route.ts        # → /api/users
```

### Dynamic Routes

```
src/app/
├── users/
│   └── [id]/               # Dynamic: /users/123
│       └── page.tsx
├── blog/
│   └── [...slug]/          # Catch-all: /blog/a/b/c
│       └── page.tsx
└── shop/
    └── [[...categories]]/  # Optional catch-all: /shop or /shop/a/b
        └── page.tsx
```

## Architecture & Development Flow

### Layered Architecture (MANDATORY)

```
Prisma Schema → Types → Server Actions/API Routes → Components → Pages
```

Always follow this flow when implementing features:

1. **Database Schema** (`prisma/schema.prisma`)
   - **APPEND new models at end of file, PRESERVE existing models**
   - Auth models (User, Account, Session, VerificationToken) are REQUIRED
   - Run `bunx prisma generate && bunx prisma db push`

2. **Type Definitions** (`src/types/api.types.ts`)
   - **NEVER overwrite existing types**
   - **ADD new types at the end of file**
   
   ```typescript
   // Zod schema for input validation
   export const productSchema = z.object({
     name: z.string().min(1, 'Name is required'),
     price: z.number().positive(),
   });
   
   // Request type (infer from Zod)
   export type ProductRequest = z.infer<typeof productSchema>;
   
   // Response type
   export interface ProductResponse {
     id: string;
     name: string;
     price: number;
   }
   ```

3. **Server Actions** (for mutations) OR **API Routes** (for external APIs)

4. **Components** (`src/components/`)
   - Server Components by default
   - Add `'use client'` only when needed

5. **Pages** (`src/app/[route]/page.tsx`)
   - Server Components for data fetching
   - Pass data to Client Components via props

## Server Actions (Next.js 15) - CRITICAL

### When to Use Server Actions
- ✅ Form submissions
- ✅ Database mutations (create, update, delete)
- ✅ Revalidating cached data
- ❌ **NEVER use for data fetching** (use Server Components instead)

### Server Action Pattern

```typescript
// src/actions/product-actions.ts
'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/prisma';
import { productSchema } from '@/types/api.types';

export async function createProduct(formData: FormData) {
  // 1. Parse and validate input (ALWAYS validate on server)
  const rawData = {
    name: formData.get('name'),
    price: Number(formData.get('price')),
  };
  
  const validated = productSchema.safeParse(rawData);
  if (!validated.success) {
    return { error: validated.error.flatten().fieldErrors };
  }
  
  // 2. Perform mutation
  try {
    const product = await prisma.product.create({
      data: validated.data,
    });
    
    // 3. Revalidate cache
    revalidatePath('/products');
    
    return { success: true, data: product };
  } catch (error) {
    return { error: 'Failed to create product' };
  }
}

export async function deleteProduct(id: string) {
  try {
    await prisma.product.delete({ where: { id } });
    revalidatePath('/products');
    return { success: true };
  } catch (error) {
    return { error: 'Failed to delete product' };
  }
}
```

### Using Server Actions in Components

```typescript
// src/app/products/new/page.tsx (Server Component)
import { createProduct } from '@/actions/product-actions';
import { ProductForm } from '@/components/product-form';

export default function NewProductPage() {
  return <ProductForm action={createProduct} />;
}

// src/components/product-form.tsx (Client Component)
'use client';

import { useFormStatus } from 'react-dom';
import { useActionState } from 'react';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Creating...' : 'Create Product'}
    </button>
  );
}

export function ProductForm({ action }: { action: typeof createProduct }) {
  const [state, formAction] = useActionState(action, null);
  
  return (
    <form action={formAction}>
      <input name="name" required />
      <input name="price" type="number" required />
      {state?.error && <p className="text-red-500">{state.error}</p>}
      <SubmitButton />
    </form>
  );
}
```

## Data Fetching (Server-First Approach)

### Fetch in Server Components (RECOMMENDED)

```typescript
// src/app/products/page.tsx (Server Component - NO 'use client')
import { prisma } from '@/lib/prisma';
import { ProductList } from '@/components/product-list';

export default async function ProductsPage() {
  // Fetch directly in Server Component - no API needed!
  const products = await prisma.product.findMany({
    orderBy: { createdAt: 'desc' },
  });
  
  return (
    <div>
      <h1>Products</h1>
      <ProductList products={products} />
    </div>
  );
}

// src/app/products/loading.tsx (Loading state)
export default function Loading() {
  return <div>Loading products...</div>;
}

// src/app/products/error.tsx (Error boundary - MUST be Client Component)
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  );
}
```

### With Dynamic Params

```typescript
// src/app/products/[id]/page.tsx
import { prisma } from '@/lib/prisma';
import { notFound } from 'next/navigation';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function ProductPage({ params }: Props) {
  const { id } = await params;
  
  const product = await prisma.product.findUnique({
    where: { id },
  });
  
  if (!product) {
    notFound(); // Shows not-found.tsx
  }
  
  return <ProductDetail product={product} />;
}

// Generate static params for SSG
export async function generateStaticParams() {
  const products = await prisma.product.findMany({ select: { id: true } });
  return products.map((p) => ({ id: p.id }));
}
```

## API Routes (Use when needed for external APIs)

```typescript
// src/app/api/products/route.ts
import { NextRequest } from 'next/server';
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';
import { prisma } from '@/lib/prisma';
import { productSchema } from '@/types/api.types';

export async function GET() {
  try {
    const products = await prisma.product.findMany();
    return successResponse(products);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const validated = productSchema.parse(body); // Throws if invalid
    
    const product = await prisma.product.create({ data: validated });
    return successResponse(product, 'Product created', 201);
  } catch (error) {
    return handleError(error);
  }
}

// src/app/api/products/[id]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const product = await prisma.product.findUnique({ where: { id } });
    
    if (!product) {
      throw ApiErrors.notFound('Product');
    }
    
    return successResponse(product);
  } catch (error) {
    return handleError(error);
  }
}
```

## Component Patterns

### Server Component (Default)

```typescript
// src/components/product-card.tsx (Server Component - no directive needed)
import { Product } from '@prisma/client';
import { formatPrice } from '@/lib/utils';

interface Props {
  product: Product;
}

export function ProductCard({ product }: Props) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-semibold">{product.name}</h3>
      <p className="text-muted-foreground">{formatPrice(product.price)}</p>
    </div>
  );
}
```

### Client Component (Only when needed)

```typescript
// src/components/add-to-cart-button.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  productId: string;
}

export function AddToCartButton({ productId }: Props) {
  const [isLoading, setIsLoading] = useState(false);
  
  async function handleClick() {
    setIsLoading(true);
    // Add to cart logic
    setIsLoading(false);
  }
  
  return (
    <Button onClick={handleClick} disabled={isLoading}>
      {isLoading ? 'Adding...' : 'Add to Cart'}
    </Button>
  );
}
```

### Combining Server and Client Components

```typescript
// src/app/products/[id]/page.tsx (Server Component)
import { prisma } from '@/lib/prisma';
import { ProductCard } from '@/components/product-card';
import { AddToCartButton } from '@/components/add-to-cart-button';

export default async function ProductPage({ params }: Props) {
  const { id } = await params;
  const product = await prisma.product.findUnique({ where: { id } });
  
  return (
    <div>
      {/* Server Component - renders on server */}
      <ProductCard product={product} />
      
      {/* Client Component - hydrates on client */}
      <AddToCartButton productId={product.id} />
    </div>
  );
}
```

## Authentication (NextAuth v5)

**Key Files:**
- `src/auth.ts` - NextAuth configuration
- `src/middleware.ts` - Route protection
- `prisma/schema.prisma` - Auth models (DO NOT modify)

```typescript
// Server Component
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();
  
  if (!session) {
    redirect('/login');
  }
  
  return <div>Welcome {session.user.name}</div>;
}

// Client Component
'use client';
import { useSession, signOut } from 'next-auth/react';

export function UserMenu() {
  const { data: session, status } = useSession();
  
  if (status === 'loading') return <div>Loading...</div>;
  if (!session) return <LoginButton />;
  
  return (
    <div>
      <span>{session.user.name}</span>
      <button onClick={() => signOut()}>Sign out</button>
    </div>
  );
}
```

## Caching & Revalidation

```typescript
// Revalidate specific path after mutation
import { revalidatePath } from 'next/cache';
revalidatePath('/products');

// Revalidate by tag
import { revalidateTag } from 'next/cache';

// In data fetching
const products = await prisma.product.findMany();
// Tag this data
export const dynamic = 'force-dynamic'; // or use unstable_cache with tags

// After mutation
revalidateTag('products');
```

## Code Conventions

### TypeScript
- Strict mode enabled - no implicit `any`
- Use `unknown` instead of `any`
- Always define explicit types

### Import Paths
```typescript
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { createProduct } from '@/actions/product-actions';
```

### Styling
- Use Tailwind utility classes
- Use `cn()` from `@/lib/utils` for conditional classes
- shadcn/ui components use "new-york" style

## Testing Guidelines

```typescript
// Component test
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('ProductForm', () => {
  it('submits form data', async () => {
    const user = userEvent.setup();
    render(<ProductForm action={mockAction} />);
    
    await user.type(screen.getByLabelText('Name'), 'Test Product');
    await user.click(screen.getByRole('button', { name: /create/i }));
    
    expect(mockAction).toHaveBeenCalled();
  });
});
```

## Project Structure

```
src/
├── app/
│   ├── (auth)/           # Auth route group
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/      # Dashboard route group
│   │   └── settings/
│   ├── api/              # API routes
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Home page
│   ├── loading.tsx       # Global loading
│   └── error.tsx         # Global error
├── actions/              # Server Actions
│   └── product-actions.ts
├── components/
│   ├── ui/               # shadcn/ui components
│   └── [feature]/        # Feature components
├── lib/
│   ├── api-response.ts   # API helpers
│   ├── prisma.ts         # Prisma client
│   └── utils.ts          # Utilities
├── types/
│   └── api.types.ts      # Types & Zod schemas
├── auth.ts               # NextAuth config
└── middleware.ts         # Route protection
```

## Critical Rules

1. **Server Actions for mutations ONLY** - Never fetch data with Server Actions
2. **Server Components for data fetching** - Use Prisma directly, no API calls
3. **Always validate inputs** - Use Zod on server side
4. **Always use revalidatePath/revalidateTag** - After mutations
5. **Never skip Prisma generation** - Run `bunx prisma generate` after schema changes
6. **PRESERVE existing code** - Append new types/models, don't overwrite
7. **Use existing shadcn/ui components** - Before creating custom ones
8. **Test new features** - Write tests before committing
