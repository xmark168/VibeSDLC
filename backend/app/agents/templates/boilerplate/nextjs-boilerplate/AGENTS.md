## Project Overview

Next.js 16 boilerplate with TypeScript, App Router, Prisma, NextAuth v5, Tailwind CSS 4, and shadcn/ui components. Uses bun as package manager.

**Key Stack:**
- Next.js 16.0.3 + React 19.2.0
- NextAuth v5 (beta) with Credentials provider + Prisma adapter
- Prisma ORM + PostgreSQL
- Tailwind CSS 4 + 50+ shadcn/ui components (Radix UI)
- React Hook Form + Zod validation
- Zustand for state management
- Jest 30 + React Testing Library

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

# Linting
bun lint                 # Run ESLint

# Database (Prisma)
npx prisma generate      # Generate Prisma Client (after schema changes)
npx prisma db push       # Push schema changes to database (dev)
npx prisma migrate dev   # Create and apply migrations (production-ready)
npx prisma studio        # Open Prisma Studio GUI
```

## Architecture & Development Flow

### Layered Architecture (MANDATORY)

```
Prisma Schema → Types → API Routes → Services → Components → Pages
```

Always follow this flow when implementing features:

1. **Database Schema** (`prisma/schema.prisma`)
   - **When adding models**: APPEND at end of file, PRESERVE existing models
   - Auth models (User, Account, Session, VerificationToken) are REQUIRED - do not remove
   - Run `npx prisma generate && npx prisma db push`
   - Use camelCase for field names

2. **Type Definitions** (`src/types/api.types.ts`)
   - **NEVER overwrite existing types** (ApiResponse, ApiError, HttpStatus, PaginationMeta, etc.)
   - **ADD new types at the end of file** following this format:
   
   ```typescript
   /**
    * [FEATURE_NAME] - e.g., PRODUCT, ORDER, etc.
    */
   
   // Zod schema for input validation
   export const [feature]Schema = z.object({
     field1: z.string().min(1, 'Field1 is required'),
     field2: z.number().positive(),
   });
   
   // Request type (infer from Zod schema)
   export type [Feature]Request = z.infer<typeof [feature]Schema>;
   
   // Response type (what API returns)
   export interface [Feature]Response {
     id: string;
     // ... other fields
   }
   ```
   
   - Use **PascalCase** for interfaces/types, **camelCase** for Zod schemas
   - Group related types with section comments

3. **API Routes** (`src/app/api/[resource]/route.ts`)
   - Use type-safe response helpers from `@/lib/api-response.ts`
   - Always validate input with Zod schemas
   - See "API Response Patterns" below

4. **Services** (`src/services/`) - Optional
   - Extract complex business logic from API routes
   - Keep API routes thin

5. **Components** (`src/components/`)
   - Server Components by default
   - Add `'use client'` directive only when needed (interactivity, hooks, browser APIs)
   - Use existing shadcn/ui components before creating custom ones

6. **Pages** (`src/app/[route]/page.tsx`)
   - Server Components by default for data fetching
   - Pass data down to Client Components via props

### API Response Patterns

**Always use these helpers from `@/lib/api-response.ts`:**

```typescript
import { successResponse, errorResponse, handleError, ApiErrors } from '@/lib/api-response';

// Success response
return successResponse(data, 'Optional message', HttpStatus.OK);

// Error responses
throw ApiErrors.notFound('User');
throw ApiErrors.unauthorized();
throw ApiErrors.forbidden();
throw ApiErrors.validation('Invalid input', { field: 'email' });

// Generic error handling in catch blocks
try {
  // ... your code
} catch (error) {
  return handleError(error); // Handles Zod, ApiException, and generic errors
}
```

### Authentication Architecture (NextAuth v5)

**Key Files:**
- `src/auth.ts` - NextAuth configuration with Credentials provider
- `src/middleware.ts` - Route protection middleware
- `prisma/schema.prisma` - User, Account, Session, VerificationToken models

**Authentication Flow:**
- JWT-based sessions (`strategy: "jwt"`)
- Passwords hashed with bcryptjs
- Custom login page at `/login`
- Middleware protects all routes except `/api`, `/_next/static`, `/_next/image`, `/favicon.ico`

**Usage in Server Components:**
```typescript
import { auth } from '@/auth';

const session = await auth();
if (!session) {
  // User not authenticated
}
```

**Usage in Client Components:**
```typescript
'use client';
import { useSession } from 'next-auth/react';

const { data: session, status } = useSession();
```

## Code Conventions

### TypeScript
- Strict mode enabled - no implicit `any`
- Use `unknown` instead of `any` for type safety
- Always define explicit types for function parameters and return values

### Import Paths
Use `@/*` alias for all imports from `src/`:
```typescript
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { successResponse } from '@/lib/api-response';
```

### Component Patterns
```typescript
// Server Component (default) - no 'use client'
export default async function Page() {
  const data = await prisma.user.findMany();
  return <ClientComponent data={data} />;
}

// Client Component - requires 'use client'
'use client';
export function ClientComponent({ data }: { data: User[] }) {
  const [state, setState] = useState();
  return <div>...</div>;
}
```

### Form Handling Pattern
```typescript
'use client';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  username: z.string().min(3),
  password: z.string().min(6),
});

type FormData = z.infer<typeof schema>;

export function MyForm() {
  const form = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    const response = await fetch('/api/endpoint', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    // handle response
  }
}
```

### Styling
- Use Tailwind utility classes
- Use `cn()` from `@/lib/utils` to merge classes conditionally
- shadcn/ui components use "new-york" style variant
- Theme via CSS variables (supports dark mode with next-themes)

## Testing Guidelines

**Test Location:**
- Place tests in `__tests__/` folders or co-locate with source files
- Naming: `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`

**Pre-mocked Modules:**
- `next/navigation` (useRouter, usePathname, useSearchParams)
- `window.matchMedia`
- `IntersectionObserver`
- `ResizeObserver`

**Component Testing:**
```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('MyComponent', () => {
  it('handles interactions', async () => {
    const user = userEvent.setup();
    render(<MyComponent />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Result')).toBeInTheDocument();
  });
});
```

**Run tests before committing** - Test coverage thresholds are currently at 0% but aim for meaningful test coverage on new code.

## Database Workflow

1. Edit `prisma/schema.prisma`
2. Generate client: `npx prisma generate`
3. Push changes: `npx prisma db push` (dev) or `npx prisma migrate dev` (prod)
4. Access Prisma Client via `@/lib/prisma`:

```typescript
import { prisma } from '@/lib/prisma';

const users = await prisma.user.findMany();
```

## Environment Variables

Required `.env` file:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
NODE_ENV="development"
AUTH_SECRET="your-secret-key"  # For NextAuth
```

## Project Structure

```
src/
├── app/
│   ├── api/              # API routes
│   ├── layout.tsx        # Root layout with SessionProvider
│   └── page.tsx          # Home page
├── components/
│   ├── ui/               # 50+ shadcn/ui components
│   └── [custom]/         # Custom components
├── lib/
│   ├── api-response.ts   # API response helpers (ALWAYS use these)
│   ├── auth-helpers.ts   # Auth utility functions
│   ├── prisma.ts         # Prisma client instance
│   └── utils.ts          # cn() and other utils
├── types/
│   ├── api.types.ts      # API types, Zod schemas
│   └── next-auth.d.ts    # NextAuth type extensions
├── auth.ts               # NextAuth configuration
└── middleware.ts         # Route protection
```

## Critical Patterns

1. **Never skip Prisma generation** - Always run `npx prisma generate` after schema changes
2. **Always use API response helpers** - Never manually construct NextResponse for API routes
3. **Validate all API inputs** - Use Zod schemas defined in `@/types/api.types.ts`
4. **Server-first approach** - Default to Server Components, only use Client Components when necessary
5. **Type safety** - Leverage Prisma-generated types, avoid `any`
6. **Test new code** - Write tests for new features before committing

## Additional Notes

- This is a boilerplate template - adapt patterns as needed for specific use cases
- The project uses Vietnamese comments in some files (api-response.ts) - maintain consistency or update as preferred
- Package manager is **bun** - use `bun` instead of `npm` or `yarn`
- Turbopack is enabled by default (`bun dev`) for faster development
