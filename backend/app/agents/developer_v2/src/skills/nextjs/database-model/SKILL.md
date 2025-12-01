---
name: database-model
description: Create Prisma schema models with proper relations, indexes, and type safety for Next.js 16
triggers:
  - prisma
  - schema
  - model
  - database
  - db
  - relation
  - migration
  - entity
version: "2.0"
author: VibeSDLC
---

# Database Model Skill (Prisma + Next.js 16)

## Critical Rules

1. **File location** - Models in `prisma/schema.prisma`
2. **Naming** - PascalCase for models, camelCase for fields
3. **ID field** - Use `cuid()` or `uuid()` for primary keys
4. **Timestamps** - Always add `createdAt` and `updatedAt`
5. **Indexes** - Add `@@index` for frequently queried fields
6. **Relations** - Define both sides of relations
7. **After changes** - Run `bunx prisma generate && bunx prisma db push`

## Basic Model Pattern

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String
  role      Role     @default(USER)
  avatar    String?
  isActive  Boolean  @default(true)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  // Relations
  posts     Post[]
  comments  Comment[]
  profile   Profile?

  // Indexes for query performance
  @@index([email])
  @@index([role])
  @@index([createdAt])
}

enum Role {
  USER
  ADMIN
  MODERATOR
}
```

## One-to-Many Relation

```prisma
model User {
  id    String @id @default(cuid())
  email String @unique
  name  String
  
  posts Post[] // One user has many posts
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  
  // Foreign key relation
  author    User     @relation(fields: [authorId], references: [id], onDelete: Cascade)
  authorId  String
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([authorId])
  @@index([published])
}
```

## One-to-One Relation

```prisma
model User {
  id      String   @id @default(cuid())
  email   String   @unique
  
  profile Profile? // Optional one-to-one
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Profile {
  id       String  @id @default(cuid())
  bio      String?
  website  String?
  location String?
  
  // One-to-one relation
  user     User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId   String  @unique // Unique for one-to-one
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

## Many-to-Many Relation (Implicit)

```prisma
model Post {
  id         String     @id @default(cuid())
  title      String
  
  categories Category[] // Many-to-many (implicit)
  
  createdAt  DateTime   @default(now())
  updatedAt  DateTime   @updatedAt
}

model Category {
  id    String @id @default(cuid())
  name  String @unique
  slug  String @unique
  
  posts Post[] // Many-to-many (implicit)
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

## Many-to-Many Relation (Explicit - with extra fields)

```prisma
model User {
  id          String       @id @default(cuid())
  email       String       @unique
  
  memberships Membership[] // Through table
  
  createdAt   DateTime     @default(now())
  updatedAt   DateTime     @updatedAt
}

model Team {
  id          String       @id @default(cuid())
  name        String
  
  memberships Membership[] // Through table
  
  createdAt   DateTime     @default(now())
  updatedAt   DateTime     @updatedAt
}

// Explicit join table with extra fields
model Membership {
  id        String   @id @default(cuid())
  role      String   @default("member") // Extra field
  joinedAt  DateTime @default(now())    // Extra field
  
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId    String
  
  team      Team     @relation(fields: [teamId], references: [id], onDelete: Cascade)
  teamId    String
  
  @@unique([userId, teamId]) // Prevent duplicate memberships
  @@index([userId])
  @@index([teamId])
}
```

## Self-Relation (Comments/Replies)

```prisma
model Comment {
  id        String    @id @default(cuid())
  content   String
  
  // Self-relation for replies
  parent    Comment?  @relation("CommentReplies", fields: [parentId], references: [id], onDelete: Cascade)
  parentId  String?
  replies   Comment[] @relation("CommentReplies")
  
  // Author relation
  author    User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  authorId  String
  
  // Post relation
  post      Post      @relation(fields: [postId], references: [id], onDelete: Cascade)
  postId    String
  
  createdAt DateTime  @default(now())
  updatedAt DateTime  @updatedAt

  @@index([parentId])
  @@index([authorId])
  @@index([postId])
}
```

## Prisma Client Usage

```typescript
// lib/prisma.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}
```

## Common Query Patterns

```typescript
// Create with relation
const user = await prisma.user.create({
  data: {
    email: 'user@example.com',
    name: 'John',
    profile: {
      create: { bio: 'Hello world' },
    },
  },
  include: { profile: true },
});

// Find with relations (avoid N+1)
const posts = await prisma.post.findMany({
  include: {
    author: { select: { id: true, name: true } },
    categories: true,
  },
});

// Update nested
const updated = await prisma.user.update({
  where: { id: 'user-id' },
  data: {
    profile: {
      upsert: {
        create: { bio: 'New bio' },
        update: { bio: 'Updated bio' },
      },
    },
  },
});

// Delete cascade (if onDelete: Cascade)
await prisma.user.delete({ where: { id: 'user-id' } });
```

## Commands After Schema Changes

```bash
# Generate Prisma Client (after schema changes)
bunx prisma generate

# Push schema to database (development)
bunx prisma db push

# Create migration (production)
bunx prisma migrate dev --name add_user_model

# View database
bunx prisma studio
```

## Field Type Reference

| Type | Prisma | PostgreSQL |
|------|--------|------------|
| String | `String` | `text` |
| Integer | `Int` | `integer` |
| Float | `Float` | `double precision` |
| Boolean | `Boolean` | `boolean` |
| DateTime | `DateTime` | `timestamp` |
| JSON | `Json` | `jsonb` |
| Enum | `enum Name {}` | `enum` |
| Optional | `String?` | nullable |
| Array | `String[]` | `text[]` |
