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

## When NOT to Use This Skill (During Implementation)

During `implement` phase, do NOT run these commands - they run automatically in validation phase:

- `bunx prisma db push` - runs automatically after all code is written
- `bunx prisma generate` - runs automatically after all code is written
- `bun run typecheck` - runs automatically in validation
- `bun run lint` - runs automatically in validation
- `bun run build` - runs automatically in validation

Only use this skill during implementation for:
- Installing NEW dependencies (`bun add <package>`)
- Running specific unit tests for debugging
- Checking package.json contents

## Pre-installed Packages

Do NOT install packages already in the boilerplate:
- **Database**: `prisma`, `@prisma/client`
- **Auth**: `next-auth`, `@auth/prisma-adapter`
- **Forms**: `zod`, `react-hook-form`, `@hookform/resolvers`
- **UI**: All `@radix-ui/*`, `lucide-react`, `sonner`, `cmdk`
- **Styling**: `tailwind-merge`, `clsx`, `class-variance-authority`
- **Animation**: `framer-motion`
- **Carousel**: `embla-carousel-react` (for Carousel component)
- **Date**: `react-day-picker` (for Calendar component)

**All 53 shadcn/ui components are pre-installed** at `@/components/ui/*`:
accordion, alert, alert-dialog, aspect-ratio, avatar, badge, breadcrumb, button, button-group, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, empty, field, form, hover-card, input, input-group, input-otp, item, kbd, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, spinner, switch, table, tabs, textarea, toggle, toggle-group, tooltip

Only add packages when:
- Package is NOT in `package.json`
- Story explicitly requires a new package

## When TO Install Packages

MUST install with `bun add <package>` BEFORE writing code that imports it:

- Importing a package not in pre-installed list above
- Story requires specific library not in boilerplate

**Example workflow:**
```
1. Check if package is in pre-installed list
2. If NOT: execute_shell("bun add date-fns")
3. THEN: Write file with the import
```

**Common packages that need installation:**
- `date-fns` or `dayjs` - Date formatting/manipulation
- `@tanstack/react-query` - Data fetching with caching
- `axios` - HTTP client (if not using fetch)
- `recharts` - Charts library (if not using chart component)

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
- Run prisma db push/generate during implementation (handled by validation phase)
- Retry database commands when database is not running

**IMPORTANT**: Prisma generate and db push run automatically in validation phase. Do NOT run them manually during implementation.
