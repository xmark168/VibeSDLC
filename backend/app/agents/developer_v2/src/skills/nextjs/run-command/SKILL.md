---
name: run-command
description: Execute shell commands in Next.js project with Bun. Use when running install, build, test, lint, prisma commands, or adding dependencies.
---

# Run Commands (Bun)

## Critical Rules

1. **ONLY use**: `bun` and `bunx`
2. **NEVER use**: npm, npx, yarn, pnpm
3. **Check success**: Verify exit code before continuing
4. **Order matters**: install - generate - build - test

## Before Installing Packages

**DON'T install packages that are already in boilerplate:**

Already installed (DON'T `bun add` again):
- `prisma`, `@prisma/client` - Database
- `next-auth`, `@auth/prisma-adapter` - Auth
- `zod`, `react-hook-form`, `@hookform/resolvers` - Forms
- `lucide-react` - Icons
- `sonner` - Toast notifications
- `framer-motion` - Animations
- All `@radix-ui/*` - shadcn/ui dependencies
- `tailwind-merge`, `clsx`, `class-variance-authority` - Styling

**Only `bun add` when:**
- Package is NOT in `package.json`
- Story explicitly requires new package

## Command Reference

### Package Management

| Task | Command |
|------|---------|
| Install all | `bun install` |
| Add dependency | `bun add <package>` |
| Add dev dep | `bun add -d <package>` |
| Remove | `bun remove <package>` |

### Development

| Task | Command |
|------|---------|
| Dev server | `bun run dev` |
| Build | `bun run build` |
| Start prod | `bun run start` |

### Testing & Quality

| Task | Command |
|------|---------|
| Test all | `bun run test` |
| Test watch | `bun run test --watch` |
| Test file | `bun run test <path>` |
| Lint | `bun run lint` |
| Lint fix | `bun run lint:fix` |
| Format | `bun run format` |
| Type check | `bun run typecheck` |

### Prisma Commands

| Task | Command | When to Use |
|------|---------|-------------|
| Generate | `bunx prisma generate` | After schema.prisma changes |
| Push | `bunx prisma db push` | Quick prototyping (no migration) |
| Migrate | `bunx prisma migrate dev` | Create migration with history |
| Deploy | `bunx prisma migrate deploy` | Production deployment |

## Error Handling

### Skip These Errors (Don't Retry)

| Error Pattern | Meaning | Action |
|---------------|---------|--------|
| `connection refused` | Database not running | Skip command |
| `ECONNREFUSED` | Service unavailable | Skip command |
| `P1001: Can't reach database` | No database | Skip command |
| `ENOENT: no such file` | File missing | Skip command |

### Retry After Fix

| Error Pattern | Meaning | Fix |
|---------------|---------|-----|
| `Module not found` | Missing deps | Run `bun install` |
| `Cannot find module` | Missing deps | Run `bun install` |
| `command not found: prisma` | Missing deps | Run `bun install` |

## Command Dependencies

```
bun install
    ↓
bunx prisma generate (if schema exists)
    ↓
bun run build
    ↓
bun run test
```

## Examples

```bash
# Install and build
bun install
bun run build

# After schema change
bunx prisma generate
bunx prisma db push

# Run specific test
bun run test src/__tests__/api/users.test.ts

# Fix lint issues
bun run lint:fix
```
