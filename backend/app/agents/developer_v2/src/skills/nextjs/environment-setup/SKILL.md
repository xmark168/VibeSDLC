---
name: environment-setup
description: Setup environment variables for Next.js projects. Use when creating .env files or configuring environment for development/testing.
---

# Environment Setup (Next.js)

## Critical Rules

1. **File**: `.env` at project root
2. **Never commit secrets** - Use placeholder values for development
3. **NEXT_PUBLIC_** prefix for client-side vars
4. **Prisma requires** DATABASE_URL

## Quick Reference

### Development .env Template

```env
# Database - Prisma
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app

# NextAuth
AUTH_SECRET=dev-secret-key-for-testing-only
AUTH_URL=http://localhost:3000

# Public vars (accessible in browser)
NEXT_PUBLIC_BASE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

### Required Variables

| Variable | Required By | Example |
|----------|-------------|---------|
| DATABASE_URL | Prisma | `postgresql://user:pass@host:port/db` |
| AUTH_SECRET | NextAuth | Any random string (32+ chars) |
| AUTH_URL | NextAuth | `http://localhost:3000` |
| NEXT_PUBLIC_BASE_URL | Client | `http://localhost:3000` |

### Port Notes

- Default DB port: `5432` (may change if occupied)
- Default App port: `3000`
- Container will override DATABASE_URL at runtime if needed

### Usage in Code

```typescript
// Server-side (API routes, Server Actions)
const dbUrl = process.env.DATABASE_URL;

// Client-side (must have NEXT_PUBLIC_ prefix)
const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
```

### Commands

```bash
# Prisma uses DATABASE_URL automatically
bunx prisma generate
bunx prisma db push
```
