---
name: run-command
description: Execute shell commands in Next.js project. Use when running any CLI command like install, build, test, lint, prisma, or any package execution.
---

# Run Commands (Next.js + Bun)

## Package Manager: BUN

**CRITICAL**: Use `bun` and `bunx`, NEVER npm/npx/yarn/pnpm.

## Common Commands

| Task | Command |
|------|---------|
| Install deps | `bun install` |
| Dev server | `bun run dev` |
| Build | `bun run build` |
| Test | `bun run test` |
| Lint | `bun run lint` |
| Lint fix | `bunx eslint --fix .` |
| Format | `bunx prettier --write .` |

## Prisma Commands

```bash
bunx prisma generate      # Generate client
bunx prisma db push       # Push schema (dev)
bunx prisma migrate dev   # Create migration
bunx prisma studio        # View database
```

## Package Execution

```bash
# CORRECT (bunx)
bunx prisma generate
bunx eslint --fix .
bunx tsc --noEmit

# WRONG (npx) - NEVER USE
npx prisma generate  ❌
npx eslint --fix .   ❌
```

## Add Dependencies

```bash
bun add <package>           # Production dep
bun add -d <package>        # Dev dep
bun add @types/<package>    # Type definitions
```
