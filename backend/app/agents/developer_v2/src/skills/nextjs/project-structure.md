# Next.js 16 Project Structure

## Runtime

**CRITICAL**: This project uses pnpm exclusively.
- Package manager: `pnpm install`
- Run scripts: `pnpm run <script>` or `pnpm exec <command>`
- NEVER use npm, npx, yarn, or bun

## Directory Structure

```
prisma/
  schema.prisma          # Database models (has url = env("DATABASE_URL"))

src/
  app/
    api/[resource]/route.ts    # REST API handlers
    actions/[domain].ts        # Server Actions
    [route]/page.tsx           # Pages (async supported)
    layout.tsx                 # Root layout
  components/
    ui/                        # shadcn/ui - DO NOT MODIFY
    [Feature]/                 # Feature components (PascalCase)
  lib/
    prisma.ts                  # Prisma client singleton
    utils.ts                   # cn() utility
  auth.ts                      # NextAuth v5 config
  middleware.ts                # Route protection
  types/                       # TypeScript types
  __tests__/                   # Jest tests
```

## File Patterns

| Type | Path | Export |
|------|------|--------|
| Page | `app/[route]/page.tsx` | `export default` |
| API | `app/api/[resource]/route.ts` | `export async function GET/POST` |
| Action | `app/actions/[domain].ts` | Named exports |
| Component | `components/[Feature]/Name.tsx` | `export function Name` |

## Imports

```typescript
import { Button } from '@/components/ui/button';
import { prisma } from '@/lib/prisma';
import { cn } from '@/lib/utils';
import { auth } from '@/auth';
```

## Key Files

| File | Purpose |
|------|---------|
| `auth.ts` | NextAuth v5 config |
| `middleware.ts` | Protect routes |
| `lib/prisma.ts` | Database client |
| `prisma/schema.prisma` | Database models |
