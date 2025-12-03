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

### .env Template (Development)
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app

# NextAuth
AUTH_SECRET=dev-secret-key-for-testing-only
AUTH_URL=http://localhost:3000

# Public (accessible in browser)
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

### Usage
```typescript
// Server-side only (API routes, server actions, server components)
const dbUrl = process.env.DATABASE_URL;

// Client-side (NEXT_PUBLIC_ prefix required)
const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
```

## Type-Safe Env Validation (Recommended)

```typescript
// lib/env.ts
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  AUTH_SECRET: z.string().min(32),
  AUTH_URL: z.string().url(),
  NEXT_PUBLIC_BASE_URL: z.string().url(),
});

export const env = envSchema.parse({
  DATABASE_URL: process.env.DATABASE_URL,
  AUTH_SECRET: process.env.AUTH_SECRET,
  AUTH_URL: process.env.AUTH_URL,
  NEXT_PUBLIC_BASE_URL: process.env.NEXT_PUBLIC_BASE_URL,
});

// Usage: import { env } from '@/lib/env';
// env.DATABASE_URL - fully typed!
```

## Common Variables

| Variable | Required By | Example |
|----------|-------------|---------|
| DATABASE_URL | Prisma | `postgresql://user:pass@host:port/db` |
| AUTH_SECRET | NextAuth | Random 32+ char string |
| AUTH_URL | NextAuth | `http://localhost:3000` |
| NEXT_PUBLIC_* | Client | Any public config |

## Production vs Development

| Environment | DATABASE_URL | AUTH_SECRET |
|-------------|--------------|-------------|
| Development | localhost:5432 | `dev-secret-key` |
| Production | Cloud DB URL | `openssl rand -base64 32` |

## Security Rules

1. **NEVER** commit real secrets to git
2. **NEVER** prefix secrets with `NEXT_PUBLIC_`
3. **ALWAYS** use environment variables for:
   - Database credentials
   - API keys (Stripe, AWS, etc.)
   - Auth secrets
4. **Use .env.example** for documenting required vars (without values)
