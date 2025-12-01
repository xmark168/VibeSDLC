# Next.js 16 Project Structure

## Directory Layout

```
prisma/
    schema.prisma          # Database models (Prisma ORM)
    migrations/            # Database migrations

src/
    app/                   # Next.js App Router
        api/               # API Route Handlers
            [resource]/
                route.ts   # GET, POST, PUT, DELETE handlers
            [resource]/[id]/
                route.ts   # Dynamic route handlers
        actions/           # Server Actions
            [domain].ts    # e.g., user.ts, post.ts
        [route]/
            page.tsx       # Page component (default export)
            layout.tsx     # Layout component
            loading.tsx    # Loading UI
            error.tsx      # Error boundary
        layout.tsx         # Root layout
        page.tsx           # Home page

    components/            # React components
        ui/                # shadcn/ui components (DO NOT MODIFY)
            button.tsx
            input.tsx
            form.tsx
            dialog.tsx
            ...
        [feature]/         # Feature-specific components
            ComponentName.tsx

    hooks/                 # Custom React hooks
        use-[name].ts

    lib/                   # Utilities and helpers
        prisma.ts          # Prisma client singleton
        utils.ts           # cn() and other utilities
        api-response.ts    # API response helpers

    services/              # Business logic
        [domain].service.ts

    store/                 # Zustand state management
        use-[name]-store.ts

    types/                 # TypeScript types
        api.types.ts       # API response types
        [domain].types.ts

    __tests__/             # Test files (mirrors src structure)
        components/
        lib/
        hooks/
```

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Page | `page.tsx` | `app/users/page.tsx` |
| Layout | `layout.tsx` | `app/users/layout.tsx` |
| API Route | `route.ts` | `app/api/users/route.ts` |
| Server Action | `[domain].ts` | `app/actions/user.ts` |
| Component | `PascalCase.tsx` | `components/UserCard.tsx` |
| Hook | `use-kebab-case.ts` | `hooks/use-auth.ts` |
| Store | `use-[name]-store.ts` | `store/use-user-store.ts` |
| Utility | `kebab-case.ts` | `lib/api-response.ts` |
| Type | `[name].types.ts` | `types/user.types.ts` |
| Test | `[name].test.tsx` | `__tests__/components/Button.test.tsx` |

## Import Aliases

```typescript
// Use @/ alias for src/ imports
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { cn } from '@/lib/utils';
import { useUserStore } from '@/store/use-user-store';
import { createUser } from '@/app/actions/user';
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `prisma/schema.prisma` | Database models |
| `src/lib/prisma.ts` | Prisma client singleton |
| `src/lib/utils.ts` | `cn()` class merge utility |
| `src/lib/api-response.ts` | `successResponse()`, `errorResponse()` |
| `src/app/layout.tsx` | Root layout with providers |
| `src/components/ui/*` | shadcn/ui components (pre-installed) |
