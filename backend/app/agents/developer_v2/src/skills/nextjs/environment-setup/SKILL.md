---
name: environment-setup
description: Setup environment variables for Next.js projects. Use when creating .env files, configuring database connection, or setting up NextAuth secrets.
---

This skill guides configuration of environment variables for Next.js applications.

The user needs to set up database connections, authentication secrets, or other environment-specific configuration.

## Before You Start

Environment variables are configured in the `.env` file at project root (already created in boilerplate).

**CRITICAL**: Never commit real secrets to git. Use placeholder values for development and set real values in production environment.

## Environment File Template

```env
# Database (required for Prisma)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app

# NextAuth (required for authentication)
AUTH_SECRET=dev-secret-key-for-testing-only
AUTH_URL=http://localhost:3000

# Public variables (accessible in browser - use NEXT_PUBLIC_ prefix)
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

## Variable Access

Server-side variables (API routes, Server Actions, Server Components):

```typescript
const dbUrl = process.env.DATABASE_URL;
const authSecret = process.env.AUTH_SECRET;
```

Client-side variables (must have `NEXT_PUBLIC_` prefix):

```typescript
const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
```

## Type-Safe Validation

For production apps, validate environment variables at startup:

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
// env.DATABASE_URL - fully typed and validated!
```

## Required Variables

- **DATABASE_URL**: PostgreSQL connection string for Prisma
- **AUTH_SECRET**: Random string (32+ chars) for NextAuth session encryption
- **AUTH_URL**: Base URL for authentication callbacks

## Production Setup

Generate a secure AUTH_SECRET:

```bash
openssl rand -base64 32
```

Use environment variables from your hosting provider (Vercel, Railway, etc.) rather than `.env` files in production.

## Security Rules

NEVER:
- Commit real secrets to git
- Prefix secrets with `NEXT_PUBLIC_` (exposes to browser)
- Hardcode secrets in source code
- Log environment variables

ALWAYS:
- Use `.env.example` to document required variables (without values)
- Set real secrets in production environment only
- Use `NEXT_PUBLIC_` prefix only for truly public configuration

**IMPORTANT**: The `.env` file is included in `.gitignore` by default. Create `.env.example` with placeholder values for documentation.
