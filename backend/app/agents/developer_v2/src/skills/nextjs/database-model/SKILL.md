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

After any schema changes, run `pnpm exec prisma db push` (generate runs automatically).

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
  price     Float    // Use Float for simpler type handling in UI
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

## Type Choices for Numbers

| Type | Prisma Returns | Use Case |
|------|---------------|----------|
| `Int` | `number` | Counts, IDs, whole numbers |
| `Float` | `number` | Prices, measurements (recommended for UI) |
| `Decimal` | `Prisma.Decimal` | Financial calculations needing exact precision |

**Recommendation**: Use `Float` for prices in most apps. It returns `number` directly, no conversion needed.

If using `Decimal` (for financial apps):
- API must convert: `Number(item.price)` or `item.price.toNumber()`
- TypeScript type: `Prisma.Decimal` not `number`

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

DO NOT run db push manually during implementation.
Database operations (`prisma generate`, `prisma db push`) run automatically in validation phase.
Just write the schema file and proceed to next task.

## Seeding Data

**IMPORTANT**: After creating new models, create seed data for testing and development.

### Seed File Structure

```typescript
// prisma/seed.ts
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding database...');

  // Clear existing data (optional)
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();

  // Create categories first (parent records)
  const category1 = await prisma.category.create({
    data: {
      name: 'Mathematics',
      slug: 'mathematics',
      gradeLevel: 'Grade 6-8',
    },
  });

  const category2 = await prisma.category.create({
    data: {
      name: 'Science',
      slug: 'science',
      gradeLevel: 'Grade 6-8',
    },
  });

  // Create books with relations
  await prisma.book.createMany({
    data: [
      {
        title: 'Algebra Fundamentals',
        author: 'John Smith',
        price: 29.99,
        coverImage: 'https://picsum.photos/seed/book1/200/300',
        isFeatured: true,
        stockQuantity: 50,
        categoryId: category1.id,
      },
      {
        title: 'Physics for Beginners',
        author: 'Jane Doe',
        price: 34.99,
        coverImage: 'https://picsum.photos/seed/book2/200/300',
        isFeatured: true,
        stockQuantity: 30,
        categoryId: category2.id,
      },
      // Add 5-10 sample records for good UI testing
    ],
  });

  console.log('✅ Seeding complete!');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
```

### Seed Data Guidelines

1. **Create 5-10 records** per model for realistic UI testing
2. **Use realistic data** - proper names, prices, descriptions
3. **Include edge cases** - empty strings, nulls, long text
4. **Set `isFeatured: true`** on some records for homepage display
5. **Vary `stockQuantity`** - some in stock, some low, some out
6. **Use Picsum for images** - `https://picsum.photos/seed/{unique}/width/height`

### Image Placeholders (Picsum)

```typescript
// Consistent image per seed (same image every time)
coverImage: 'https://picsum.photos/seed/book1/200/300'
coverImage: 'https://picsum.photos/seed/book2/200/300'

// Random image each load
coverImage: 'https://picsum.photos/200/300'

// Fixed image by ID
coverImage: 'https://picsum.photos/id/24/200/300'
```

Common sizes: `200/300` (book), `400/300` (card), `100/100` (avatar)

### Running Seed

After implementation, seed runs automatically or manually:
```bash
pnpm exec tsx prisma/seed.ts
```

## Commands Reference

```bash
pnpm exec prisma generate     # Generate TypeScript types
pnpm exec prisma db push      # Push schema to database (dev)
pnpm exec prisma migrate dev  # Create migration file (when ready)
pnpm exec prisma studio       # Visual database browser
```

NEVER:
- Modify or remove the `datasource db` block (url is REQUIRED)
- Modify or remove the `generator client` block
- Recreate `lib/prisma.ts` (already exists in boilerplate)
- Recreate User/Account/Session models (already in boilerplate)
- Forget `@@index` on foreign key fields
- Skip `onDelete: Cascade` on child relations
- Create migration files (use `pnpm exec prisma db push` for dev instead)
- Run `execute_shell` for db push/generate during implementation (runs automatically in validation)

**IMPORTANT**: Always add indexes on fields used in WHERE clauses or JOINs to improve query performance.
