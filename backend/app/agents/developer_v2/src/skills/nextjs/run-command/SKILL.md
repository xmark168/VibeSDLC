---
name: run-command
description: Execute shell commands in Next.js project with Bun. Use when running install, build, test, lint, prisma commands, or adding dependencies.
---

# Run Commands (Bun)

## Critical Rules

1. **Package manager**: Use `bun` and `bunx` ONLY
2. **NEVER use**: npm, npx, yarn, pnpm

## Quick Reference

| Task | Command |
|------|---------|
| Install | `bun install` |
| Dev | `bun run dev` |
| Build | `bun run build` |
| Test | `bun run test` |
| Lint | `bun run lint` |
| Lint fix | `bunx eslint --fix .` |
| Add dep | `bun add <package>` |
| Add dev dep | `bun add -d <package>` |

## Prisma Commands

| Task | Command |
|------|---------|
| Generate | `bunx prisma generate` |
| Push schema | `bunx prisma db push` |
| Migrate | `bunx prisma migrate dev` |
| Studio | `bunx prisma studio` |
