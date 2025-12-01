---
name: database-model
description: Create Prisma schema models with relations, indexes, and type safety. Use when designing database schemas, creating migrations, or working with Prisma ORM.
---

# Database Model (Prisma)

## Critical Rules

1. **File**: `prisma/schema.prisma`
2. **Naming**: PascalCase models, camelCase fields
3. **ID**: Use `@id @default(cuid())`
4. **Timestamps**: Always add `createdAt`, `updatedAt`
5. **Indexes**: Add `@@index` for query fields
6. **After changes**: `bunx prisma generate && bunx prisma db push`

## Quick Reference

### Basic Model
```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String
  role      Role     @default(USER)
  isActive  Boolean  @default(true)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  posts     Post[]

  @@index([email])
  @@index([role])
}

enum Role {
  USER
  ADMIN
}
```

### One-to-Many
```prisma
model Post {
  id       String @id @default(cuid())
  title    String
  
  author   User   @relation(fields: [authorId], references: [id], onDelete: Cascade)
  authorId String

  @@index([authorId])
}
```

### One-to-One
```prisma
model Profile {
  id     String @id @default(cuid())
  bio    String?
  
  user   User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId String @unique  // Unique for one-to-one
}
```

### Many-to-Many
```prisma
model Post {
  id         String     @id @default(cuid())
  categories Category[]
}

model Category {
  id    String @id @default(cuid())
  name  String @unique
  posts Post[]
}
```

### Prisma Client
```typescript
// lib/prisma.ts
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
