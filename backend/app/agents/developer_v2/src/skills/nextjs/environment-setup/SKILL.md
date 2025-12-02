---
name: environment-setup
description: Setup environment variables for Next.js projects. Use when creating .env files, configuring database connection, or setting up NextAuth secrets.
---

# Environment Setup (Next.js)

## Critical Rules

1. **File**: `.env` at project root (already in boilerplate)
2. **Never commit secrets** - Use placeholder values for dev
3. **NEXT_PUBLIC_** prefix for client-side vars
4. **Prisma requires** DATABASE_URL

## Quick Reference

### .env Template
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app
AUTH_SECRET=dev-secret-key-for-testing-only
AUTH_URL=http://localhost:3000
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

### Usage
```typescript
// Server-side
const dbUrl = process.env.DATABASE_URL;

// Client-side (NEXT_PUBLIC_ prefix required)
const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
```

## Common Patterns

| Variable | Required By | Example |
|----------|-------------|---------|
| DATABASE_URL | Prisma | `postgresql://user:pass@host:port/db` |
| AUTH_SECRET | NextAuth | Random string (32+ chars) |
| AUTH_URL | NextAuth | `http://localhost:3000` |
| NEXT_PUBLIC_* | Client | Any public config |
