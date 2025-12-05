---
name: database-model
description: Create Prisma schema models with relations and indexes. Use when designing database schemas, adding models, creating migrations, or defining entity relationships.
---

This skill guides creation of Prisma database models for Next.js applications.

The user needs to design database schemas, add new models, define relationships, or modify existing tables.

## Before You Start

**CRITICAL**: The boilerplate already has correct Prisma setup. DO NOT modify the datasource block.

- **Schema file**: `prisma/schema.prisma` - MUST have `url = env("DATABASE_URL")`
- **Client file**: `lib/prisma.ts` - Already configured correctly

After any schema changes, run `bunx prisma db push` (generate runs automatically).

## Schema Structure

```prisma
// prisma/schema.prisma - DO NOT MODIFY THIS BLOCK
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")  // REQUIRED - never remove this
}

// Add your models BELOW the datasource block
```

## Model Conventions

Follow these conventions for all models:
- **Model names**: PascalCase (User, Product, OrderItem)
- **Field names**: camelCase (firstName, createdAt)
- **IDs**: Always use `@id @default(uuid())`
- **Timestamps**: Always include `createdAt` and `updatedAt`
- **Indexes**: Add `@@index` for frequently queried fields

```prisma
model Product {
  id        String   @id @default(uuid())
  name      String
  price     Decimal
  isActive  Boolean  @default(true)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  category   Category @relation(fields: [categoryId], references: [id])
  categoryId String

  @@index([categoryId])
  @@index([name])
}

enum Status {
  DRAFT
  PUBLISHED
  ARCHIVED
}
```

## Relationships

### One-to-Many

```prisma
model Category {
  id       String    @id @default(uuid())
  name     String    @unique
  products Product[]  // One category has many products
}

model Product {
  id         String   @id @default(uuid())
  category   Category @relation(fields: [categoryId], references: [id], onDelete: Cascade)
  categoryId String
  
  @@index([categoryId])
}
```

### One-to-One

```prisma
model User {
  id      String   @id @default(uuid())
  profile Profile?  // Optional one-to-one
}

model Profile {
  id     String @id @default(uuid())
  bio    String?
  user   User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId String @unique  // @unique makes it one-to-one
}
```

### Many-to-Many

```prisma
model Post {
  id   String @id @default(uuid())
  tags Tag[]   // Prisma handles junction table automatically
}

model Tag {
  id    String @id @default(uuid())
  name  String @unique
  posts Post[]
}
```

## NextAuth Models

The boilerplate includes required NextAuth models. Do NOT recreate these:

```prisma
// Already in boilerplate - User, Account, Session models
// Just add your relations to User if needed:
model User {
  id       String    @id @default(uuid())
  // ... existing fields
  posts    Post[]    // Add your relations here
  comments Comment[]
}
```

## Prisma Client Setup

The boilerplate already has `lib/prisma.ts` configured. DO NOT recreate it.

```typescript
// lib/prisma.ts - ALREADY EXISTS in boilerplate
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

## After Writing Schema

Run db push to apply schema changes:

```
execute_shell("bunx prisma db push")
```

Note: `prisma generate` runs automatically with db push. If fails, fix schema and retry.

## Commands Reference

```bash
bunx prisma generate     # Generate TypeScript types
bunx prisma db push      # Push schema to database (dev)
bunx prisma migrate dev  # Create migration file (when ready)
bunx prisma studio       # Visual database browser
```

NEVER:
- Modify or remove the `datasource db` block (url is REQUIRED)
- Modify or remove the `generator client` block
- Recreate `lib/prisma.ts` (already exists in boilerplate)
- Recreate User/Account/Session models (already in boilerplate)
- Forget `@@index` on foreign key fields
- Skip `onDelete: Cascade` on child relations
- Forget to run `prisma db push` after schema changes

**IMPORTANT**: Always add indexes on fields used in WHERE clauses or JOINs to improve query performance.
