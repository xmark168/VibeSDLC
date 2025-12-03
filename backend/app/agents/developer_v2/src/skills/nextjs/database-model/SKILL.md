---
name: database-model
description: Create Prisma schema models with relations and indexes. Use when designing database schemas, adding models, creating migrations, or defining entity relationships.
---

# Database Model (Prisma 6.x+)

## Critical Rules

1. **Schema**: `prisma/schema.prisma` - NO `url` in datasource
2. **Config**: `prisma/prisma.config.ts` - Database URL config
3. **Naming**: PascalCase models, camelCase fields
4. **ID**: Use `@id @default(uuid())`
5. **Timestamps**: Always add `createdAt`, `updatedAt`
6. **Indexes**: Add `@@index` for query fields
7. **After changes**: `bunx prisma generate && bunx prisma db push`

## Prisma 6.x Schema

```prisma
// prisma/schema.prisma - NO url in datasource
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  // url moved to prisma.config.ts
}
```

## Quick Reference

### Basic Model
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

### One-to-Many
```prisma
model Category {
  id       String    @id @default(uuid())
  name     String    @unique
  products Product[]
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
model Profile {
  id     String  @id @default(uuid())
  bio    String?
  
  user   User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId String  @unique  // Unique for one-to-one
}
```

### Many-to-Many
```prisma
model Post {
  id   String @id @default(uuid())
  tags Tag[]
}

model Tag {
  id    String @id @default(uuid())
  name  String @unique
  posts Post[]
}
```

## NextAuth Models (Required)

```prisma
// These models are required for NextAuth v5
// Already in boilerplate - DO NOT recreate

model User {
  id            String    @id @default(uuid())
  username      String    @unique
  email         String?   @unique
  emailVerified DateTime?
  password      String
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  accounts Account[]
  sessions Session[]
}

model Account {
  id                String  @id @default(uuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  // ... more fields
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  @@unique([provider, providerAccountId])
}

model Session {
  id           String   @id @default(uuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}
```

## Prisma Client (Prisma 6.x+)
```typescript
// lib/prisma.ts - requires datasourceUrl
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({
  datasourceUrl: process.env.DATABASE_URL,  // Required in Prisma 6.x+
  log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
});

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

## Commands
```bash
bunx prisma generate     # Generate client
bunx prisma db push      # Push to DB (dev)
bunx prisma migrate dev  # Create migration
bunx prisma studio       # View database
```

## References

- `prisma-patterns.md` - Relations, queries, advanced patterns
