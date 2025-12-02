# Next.js 16 Project Structure

```
prisma/schema.prisma       # Database models

src/
  app/
    api/[resource]/route.ts    # API handlers
    actions/[domain].ts        # Server Actions
    [route]/page.tsx           # Pages
    layout.tsx                 # Root layout
  components/
    ui/                        # shadcn/ui (DO NOT MODIFY)
    [feature]/                 # Feature components
  lib/
    prisma.ts                  # Prisma client
    utils.ts                   # cn() utility
    api-response.ts            # API helpers
  types/                       # TypeScript types
  __tests__/                   # Tests
```

## File Naming

| Type | Pattern |
|------|---------|
| Page | `app/[route]/page.tsx` |
| API | `app/api/[resource]/route.ts` |
| Action | `app/actions/[domain].ts` |
| Component | `components/[Feature]/Name.tsx` |

## Imports

```typescript
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { cn } from '@/lib/utils';
```
