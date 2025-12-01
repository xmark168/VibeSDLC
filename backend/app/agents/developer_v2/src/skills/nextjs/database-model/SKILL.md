---
name: database-model
description: Create Prisma schema models with relations, indexes, and type safety. Use when designing database schemas, creating migrations, or working with Prisma ORM.
---

# Database Model (Prisma)

## Critical Rules

1. **File**: `prisma/schema.prisma`
2. **Naming**: PascalCase models, camelCase fields
3. **ID**: Use `@id @default(uuid())`
4. **Timestamps**: Always add `createdAt`, `updatedAt`
5. **Indexes**: Add `@@index` for query fields
6. **After changes**: `bunx prisma generate && bunx prisma db push`

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

## Prisma Client
```typescript
// lib/prisma.ts (already in boilerplate)
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };
export const prisma = globalForPrisma.prisma ?? new PrismaClient();
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
