---
name: run-command
description: Execute shell commands in Next.js project with pnpm. Use when running install, build, test, lint, prisma commands, or adding dependencies.
---

This skill guides execution of shell commands in the Next.js project environment.

The user needs to run development commands, install packages, execute tests, or manage the database.

## Before You Start

**CRITICAL**: This project uses pnpm exclusively. Never use npm, npx, yarn, or bun.

- **Package manager**: `pnpm` and `pnpm exec` only
- **Command order**: install - generate - build - test
- **Verify success**: Always check exit code before proceeding

## When NOT to Use This Skill (During Implementation)

During `implement` phase, do NOT run these commands - they run automatically in validation phase:

- `pnpm exec prisma db push` - runs automatically after all code is written
- `pnpm exec prisma generate` - runs automatically after all code is written
- `pnpm run typecheck` - runs automatically in validation
- `pnpm run lint` - runs automatically in validation
- `pnpm run build` - runs automatically in validation

Only use this skill during implementation for:
- Installing NEW dependencies (`pnpm add <package>`)
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

MUST install with `pnpm add <package>` BEFORE writing code that imports it:

- Importing a package not in pre-installed list above
- Story requires specific library not in boilerplate

**Example workflow:**
```
1. Check if package is in pre-installed list
2. If NOT: execute_shell("pnpm add date-fns")
3. THEN: Write file with the import
```

**Common packages that need installation:**
- `date-fns` or `dayjs` - Date formatting/manipulation
- `@tanstack/react-query` - Data fetching with caching
- `axios` - HTTP client (if not using fetch)
- `recharts` - Charts library (if not using chart component)

## Package Commands

```bash
pnpm install --frozen-lockfile  # Install dependencies (use lockfile)
pnpm add <package>              # Add production dependency
pnpm add -D <package>           # Add dev dependency
pnpm remove <package>           # Remove package
```

## Development Commands

```bash
pnpm run dev              # Start development server
pnpm run build            # Build for production
pnpm run start            # Start production server
```

## Quality Commands

```bash
pnpm run test             # Run all tests
pnpm run test --watch     # Watch mode
pnpm run test <path>      # Run specific test file
pnpm run lint             # Check for lint errors
pnpm run lint:fix         # Fix lint errors
pnpm run format           # Format code
pnpm run typecheck        # Check TypeScript types
```

## Prisma Commands

```bash
pnpm exec prisma generate     # Generate TypeScript client (after schema changes)
pnpm exec prisma db push      # Push schema to database (development)
pnpm exec prisma migrate dev  # Create migration with history
pnpm exec prisma migrate deploy  # Apply migrations (production)
pnpm exec prisma studio       # Open visual database browser
```

## Command Order

Always follow this sequence:

```
1. pnpm install --frozen-lockfile
2. pnpm exec prisma generate (if schema exists)
3. pnpm run build
4. pnpm run test
```

## Error Handling

**Skip these errors (don't retry):**
- `connection refused` / `ECONNREFUSED` - Database not running
- `P1001: Can't reach database` - No database connection
- `ENOENT: no such file` - File doesn't exist

**Retry after fix:**
- `Module not found` - Run `pnpm install --frozen-lockfile`
- `Cannot find module` - Run `pnpm install --frozen-lockfile`
- `command not found: prisma` - Run `pnpm install --frozen-lockfile`

NEVER:
- Use npm, npx, yarn, or bun
- Install packages already in boilerplate
- Run prisma db push/generate during implementation (handled by validation phase)
- Retry database commands when database is not running

**IMPORTANT**: Prisma generate and db push run automatically in validation phase. Do NOT run them manually during implementation.
