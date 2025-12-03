---
name: run-command
description: Execute shell commands in Next.js project with Bun. Use when running install, build, test, lint, prisma commands, or adding dependencies.
---

This skill guides execution of shell commands in the Next.js project environment.

The user needs to run development commands, install packages, execute tests, or manage the database.

## Before You Start

**CRITICAL**: This project uses Bun exclusively. Never use npm, npx, yarn, or pnpm.

- **Package manager**: `bun` and `bunx` only
- **Command order**: install - generate - build - test
- **Verify success**: Always check exit code before proceeding

## Pre-installed Packages

Do NOT install packages already in the boilerplate:
- **Database**: `prisma`, `@prisma/client`
- **Auth**: `next-auth`, `@auth/prisma-adapter`
- **Forms**: `zod`, `react-hook-form`, `@hookform/resolvers`
- **UI**: All `@radix-ui/*`, `lucide-react`, `sonner`
- **Styling**: `tailwind-merge`, `clsx`, `class-variance-authority`
- **Animation**: `framer-motion`

Only add packages when:
- Package is NOT in `package.json`
- Story explicitly requires a new package

## Package Commands

```bash
bun install --frozen-lockfile  # Install dependencies (use lockfile)
bun add <package>              # Add production dependency
bun add -d <package>           # Add dev dependency
bun remove <package>           # Remove package
```

## Development Commands

```bash
bun run dev              # Start development server
bun run build            # Build for production
bun run start            # Start production server
```

## Quality Commands

```bash
bun run test             # Run all tests
bun run test --watch     # Watch mode
bun run test <path>      # Run specific test file
bun run lint             # Check for lint errors
bun run lint:fix         # Fix lint errors
bun run format           # Format code
bun run typecheck        # Check TypeScript types
```

## Prisma Commands

```bash
bunx prisma generate     # Generate TypeScript client (after schema changes)
bunx prisma db push      # Push schema to database (development)
bunx prisma migrate dev  # Create migration with history
bunx prisma migrate deploy  # Apply migrations (production)
bunx prisma studio       # Open visual database browser
```

## Command Order

Always follow this sequence:

```
1. bun install --frozen-lockfile
2. bunx prisma generate (if schema exists)
3. bun run build
4. bun run test
```

## Error Handling

**Skip these errors (don't retry):**
- `connection refused` / `ECONNREFUSED` - Database not running
- `P1001: Can't reach database` - No database connection
- `ENOENT: no such file` - File doesn't exist

**Retry after fix:**
- `Module not found` - Run `bun install --frozen-lockfile`
- `Cannot find module` - Run `bun install --frozen-lockfile`
- `command not found: prisma` - Run `bun install --frozen-lockfile`

NEVER:
- Use npm, npx, yarn, or pnpm
- Install packages already in boilerplate
- Skip `prisma generate` after schema changes
- Retry database commands when database is not running

**IMPORTANT**: After any Prisma schema change, always run both `bunx prisma generate` and `bunx prisma db push`.
