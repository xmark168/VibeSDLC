## Project Overview

Next.js 16 boilerplate with TypeScript, App Router, Prisma, NextAuth v5, Tailwind CSS 4, and shadcn/ui components. Uses Bun as package manager.

**Key Stack:**
- Next.js 16 + React 19.2
- NextAuth v5 (beta) with Credentials provider + Prisma adapter
- Prisma ORM + PostgreSQL
- Tailwind CSS 4 + 50+ shadcn/ui components (Radix UI)
- React Hook Form + Zod validation
- Zustand for state management
- Jest + React Testing Library

## Next.js 16 App Router Conventions

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
| `proxy.ts` | **NEW** Network proxy (replaces middleware.ts) |

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

## Server Actions (Next.js 16) - CRITICAL

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
- `src/proxy.ts` - Route-level proxy (routing only, not auth)
- `prisma/schema.prisma` - Auth models (DO NOT modify)

**Note:** Auth checks should be in Server Components/Actions, not proxy.

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

## Cache Components (Next.js 16 - NEW)

Enable in `next.config.ts`:
```typescript
const config = { cacheComponents: true };
```

### Using `use cache` Directive

```typescript
// Component level caching
export async function ProductList() {
  'use cache'
  const products = await prisma.product.findMany();
  return <div>{products.map(p => <ProductCard key={p.id} product={p} />)}</div>;
}

// Function level caching
export async function getCategories() {
  'use cache'
  return await prisma.category.findMany();
}

// File level - cache all exports
'use cache'
export async function Page() {
  // This entire page is cached
}
```

## Proxy (Replaces Middleware)

```typescript
// src/proxy.ts (replaces middleware.ts)
import { NextResponse, NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  // Use for route-level proxying only
  // Auth logic should be in Route Handlers or Server Actions
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*'],
};
```

**Note:** `middleware.ts` is deprecated. Use `proxy.ts` for routing/rewrites only. Move auth checks to data layer.

## Caching & Revalidation

```typescript
// Revalidate specific path after mutation
import { revalidatePath, revalidateTag, updateTag } from 'next/cache';

revalidatePath('/products');      // Revalidate path
revalidateTag('products');        // Revalidate by tag
updateTag('products', newData);   // Update tag with new data (NEW in 16)
```

## Code Conventions

### TypeScript
- Strict mode enabled - no implicit `any`
- Use `unknown` instead of `any`
- Always define explicit types

### Import/Export Conventions (CRITICAL)

This project uses **named exports** (NOT default exports).

**Export Pattern:**
```typescript
// Components - named export
export function SearchBar() { ... }

// Services/Utils - named export
export const textbookService = { ... };
export function formatPrice() { ... }

// Types - named export
export interface Textbook { ... }
export type SearchResult = { ... };
```

**Import Pattern (MUST match export):**
```typescript
// CORRECT - named imports
import { SearchBar } from '@/components/SearchBar';
import { textbookService } from '@/lib/data/textbook-service';
import { Textbook } from '@/types/api.types';
```

**WRONG - These will cause errors:**
```typescript
// WRONG - default imports (will fail with "Missing default export")
import SearchBar from '@/components/SearchBar';
import textbookService from '@/lib/data/textbook-service';

// WRONG - default exports (don't use)
export default function SearchBar() { ... }
export default { ... };
```

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

### CRITICAL: Import Rules for Tests

**This project uses NAMED EXPORTS. Tests MUST use NAMED IMPORTS.**

```typescript
// CORRECT - named import matching named export
import { SearchBar } from '@/components/SearchBar';
import { createUser } from '@/lib/auth-helpers';
import { prisma } from '@/lib/prisma';

// WRONG - will cause "Missing default export" error
import SearchBar from '@/components/SearchBar';
import createUser from '@/lib/auth-helpers';
```

### Available Test Packages
| Package | Purpose |
|---------|---------|
| `jest` | Test runner |
| `@testing-library/react` | React component testing |
| `@testing-library/jest-dom` | DOM matchers (toBeInTheDocument, etc.) |
| `@testing-library/user-event` | User interaction simulation |
| `node-mocks-http` | Next.js API routes testing |
| `@faker-js/faker` | Generate fake test data |

### CRITICAL: Use Jest Only (NOT Vitest)

**This project uses Jest. DO NOT use Vitest.**

```typescript
// WRONG - will fail
import { describe, it, expect, vi } from 'vitest';
vi.mock(...)

// CORRECT - use Jest globals (no import needed)
jest.mock(...)
```

**Jest globals available without import:**
- `describe`, `it`, `test`, `expect`
- `jest.fn()`, `jest.mock()`, `jest.spyOn()`
- `beforeEach`, `afterEach`, `beforeAll`, `afterAll`

### API Mocking (IMPORTANT - Use jest.mock, NOT MSW)

**DO NOT use MSW** - it requires BroadcastChannel polyfills and is complex to setup.

**Instead, use jest.mock() for API calls:**

```typescript
// Mock API module BEFORE imports
jest.mock('@/lib/api', () => ({
  searchProducts: jest.fn(),
  fetchUser: jest.fn(),
}));

// Import after mock
import { searchProducts } from '@/lib/api';

describe('ProductSearch', () => {
  it('displays search results', async () => {
    // Setup mock return value
    (searchProducts as jest.Mock).mockResolvedValue([
      { id: '1', name: 'Product 1' },
      { id: '2', name: 'Product 2' },
    ]);

    render(<ProductSearch />);
    
    // Trigger search
    await userEvent.type(screen.getByRole('textbox'), 'test');
    await userEvent.click(screen.getByRole('button'));
    
    // Assert results
    expect(await screen.findByText('Product 1')).toBeInTheDocument();
  });
});
```

### Test File Structure

```
src/__tests__/
├── components/    # Component tests
├── lib/           # Utility/helper tests  
├── api/           # API route tests
└── hooks/         # Custom hook tests
```

### Test Path Mapping (MUST FOLLOW)

| Source File | Test File |
|-------------|-----------|
| `src/components/X.tsx` | `src/__tests__/components/X.test.tsx` |
| `src/components/ui/X.tsx` | `src/__tests__/components/X.test.tsx` |
| `src/lib/x.ts` | `src/__tests__/lib/x.test.ts` |
| `src/lib/data/x.ts` | `src/__tests__/lib/x.test.ts` |
| `src/app/api/x/route.ts` | `src/__tests__/api/x.test.ts` |
| `src/hooks/useX.ts` | `src/__tests__/hooks/useX.test.ts` |

**WRONG:**
- `src/__tests__/SearchBar.test.tsx` (missing /components/)
- `src/__tests__/auth.test.ts` (missing /lib/)

**CORRECT:**
- `src/__tests__/components/SearchBar.test.tsx`
- `src/__tests__/lib/auth.test.ts`

### Mocking External Dependencies (IMPORTANT)

**Always mock Prisma, bcrypt, and other external services:**

```typescript
// Mock Prisma - MUST be before imports that use it
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      create: jest.fn(),
      findUnique: jest.fn(),
      findMany: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    },
    // Add other models as needed
  },
}));

// Mock bcrypt
jest.mock('bcryptjs', () => ({
  hash: jest.fn(),
  compare: jest.fn(),
}));

// Import AFTER mocks
import { createUser } from '@/lib/auth-helpers';
import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';
```

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchBar } from '@/components/SearchBar';  // Named import!

describe('SearchBar', () => {
  it('calls onSearch when form submitted', async () => {
    const mockOnSearch = jest.fn();
    const user = userEvent.setup();
    
    render(<SearchBar onSearch={mockOnSearch} />);
    
    await user.type(screen.getByRole('textbox'), 'test query');
    await user.click(screen.getByRole('button', { name: /search/i }));
    
    expect(mockOnSearch).toHaveBeenCalledWith('test query');
  });
});
```

### Service/Helper Testing (with Mocks)

```typescript
import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';

// Mocks MUST be before the import of the module being tested
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      create: jest.fn(),
      findUnique: jest.fn(),
    },
  },
}));

jest.mock('bcryptjs', () => ({
  hash: jest.fn(),
  compare: jest.fn(),
}));

// Import the module being tested AFTER mocks
import { createUser, verifyPassword } from '@/lib/auth-helpers';

describe('auth-helpers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    it('should create user with hashed password', async () => {
      const mockUser = {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        password: 'hashed-password',
        createdAt: new Date(),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'testuser',
        password: 'plainpassword',
        email: 'test@example.com',
      });

      expect(bcrypt.hash).toHaveBeenCalledWith('plainpassword', 10);
      expect(prisma.user.create).toHaveBeenCalled();
      expect(result).not.toHaveProperty('password');
    });
  });
});
```

### API Route Testing

**CRITICAL: Always provide full URL in Request constructor!**

```typescript
// WRONG - will cause "Invalid URL: undefined" error
const req = new Request('/api/products');
const req = { url: undefined };  // Missing URL

// CORRECT - always use full URL with http://localhost
const req = new Request('http://localhost/api/products');
const req = new Request('http://localhost/api/products?search=test');  // With query params
```

Mock `next/server` is pre-configured in jest.setup.ts. Use standard `Request` objects:

```typescript
// Mock dependencies first
jest.mock('@/lib/prisma', () => ({
  prisma: {
    product: {
      findMany: jest.fn(),
      create: jest.fn(),
    },
  },
}));

import { GET, POST } from '@/app/api/products/route';
import { prisma } from '@/lib/prisma';

describe('/api/products', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('GET returns products', async () => {
    const mockProducts = [{ id: '1', name: 'Product 1' }];
    (prisma.product.findMany as jest.Mock).mockResolvedValue(mockProducts);

    // CRITICAL: Use full URL - "http://localhost" prefix required!
    const req = new Request('http://localhost/api/products');
    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.data).toEqual(mockProducts);
  });

  it('GET with query params', async () => {
    const mockProducts = [{ id: '1', name: 'Test Product' }];
    (prisma.product.findMany as jest.Mock).mockResolvedValue(mockProducts);

    // Query params example - full URL required
    const req = new Request('http://localhost/api/products?search=test&limit=10');
    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(200);
  });

  it('POST creates product', async () => {
    const newProduct = { id: '1', name: 'New Product', price: 100 };
    (prisma.product.create as jest.Mock).mockResolvedValue(newProduct);

    const req = new Request('http://localhost/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'New Product', price: 100 }),
    });
    const response = await POST(req);
    const data = await response.json();

    expect(response.status).toBe(201);
    expect(data.data).toEqual(newProduct);
  });
});
```

### Using Faker for Test Data

```typescript
import { faker } from '@faker-js/faker';

// Generate mock user
const mockUser = {
  id: faker.string.uuid(),
  name: faker.person.fullName(),
  email: faker.internet.email(),
  avatar: faker.image.avatar(),
};

// Generate array of items
const mockProducts = faker.helpers.multiple(
  () => ({
    id: faker.string.uuid(),
    name: faker.commerce.productName(),
    price: faker.number.float({ min: 10, max: 100 }),
  }),
  { count: 5 }
);
```

## Error Handling

### API Response Functions (EXACT names - DO NOT change)

| Function | Usage | Status |
|----------|-------|--------|
| `successResponse(data)` | Return success | 200 |
| `successResponse(data, msg, 201)` | Created | 201 |
| `handleError(error)` | Catch-all error handler | varies |
| `ApiErrors.badRequest(msg)` | Bad request | 400 |
| `ApiErrors.unauthorized()` | Not logged in | 401 |
| `ApiErrors.forbidden()` | No permission | 403 |
| `ApiErrors.notFound(resource)` | Not found | 404 |
| `ApiErrors.conflict(msg)` | Conflict | 409 |

**WRONG - These do NOT exist:**
- `apiSuccess()` - Use `successResponse()`
- `apiError()` - Use `handleError()` or throw `ApiErrors.xxx()`
- `createResponse()` - Use `successResponse()`

### API Route Example

```typescript
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';

export async function GET() {
  try {
    const data = await prisma.product.findMany();
    return successResponse(data);  // 200 OK
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const product = await prisma.product.create({ data: body });
    return successResponse(product, 'Created', 201);
  } catch (error) {
    return handleError(error);
  }
}
```

### Server Action Error Handling

```typescript
'use server';

export async function createProduct(formData: FormData) {
  const validated = productSchema.safeParse(data);
  
  if (!validated.success) {
    return { error: validated.error.flatten().fieldErrors };
  }
  
  try {
    const product = await prisma.product.create({ data: validated.data });
    revalidatePath('/products');
    return { success: true, data: product };
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError) {
      if (error.code === 'P2002') {
        return { error: 'Product already exists' };
      }
    }
    return { error: 'Failed to create product' };
  }
}
```

## Form Handling (React Hook Form + Zod)

### Basic Form Pattern

```typescript
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { productSchema, ProductRequest } from '@/types/api.types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

export function ProductForm() {
  const form = useForm<ProductRequest>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      name: '',
      price: 0,
    },
  });

  async function onSubmit(data: ProductRequest) {
    // Handle submission
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Product name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? 'Creating...' : 'Create'}
        </Button>
      </form>
    </Form>
  );
}
```

## State Management (Zustand)

### Creating a Store

```typescript
// src/store/cart-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'quantity'>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  total: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      
      addItem: (item) => set((state) => {
        const existing = state.items.find((i) => i.id === item.id);
        if (existing) {
          return {
            items: state.items.map((i) =>
              i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i
            ),
          };
        }
        return { items: [...state.items, { ...item, quantity: 1 }] };
      }),
      
      removeItem: (id) => set((state) => ({
        items: state.items.filter((i) => i.id !== id),
      })),
      
      updateQuantity: (id, quantity) => set((state) => ({
        items: state.items.map((i) =>
          i.id === id ? { ...i, quantity } : i
        ),
      })),
      
      clearCart: () => set({ items: [] }),
      
      total: () => get().items.reduce(
        (sum, item) => sum + item.price * item.quantity, 0
      ),
    }),
    { name: 'cart-storage' }
  )
);
```

### Using Store in Components

```typescript
'use client';

import { useCartStore } from '@/store/cart-store';

export function CartButton() {
  const { items, total } = useCartStore();
  
  return (
    <button>
      Cart ({items.length}) - ${total()}
    </button>
  );
}

export function AddToCartButton({ product }: { product: Product }) {
  const addItem = useCartStore((state) => state.addItem);
  
  return (
    <button onClick={() => addItem(product)}>
      Add to Cart
    </button>
  );
}
```

## Environment Variables

### Required Variables

```bash
# .env (DO NOT commit to git)
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
AUTH_SECRET="your-random-secret-key"

# Optional
NEXTAUTH_URL="http://localhost:3000"
```

### Usage in Code

```typescript
// Server-side only (default)
const dbUrl = process.env.DATABASE_URL;

// Client-side (must prefix with NEXT_PUBLIC_)
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// Type-safe env validation (recommended)
// src/lib/env.ts
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  AUTH_SECRET: z.string().min(32),
});

export const env = envSchema.parse(process.env);
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
└── proxy.ts              # Network proxy (routing/rewrites)
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
