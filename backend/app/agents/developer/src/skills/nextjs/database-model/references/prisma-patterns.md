# Prisma Advanced Patterns

## Explicit Many-to-Many (with extra fields)

```prisma
model User {
  id          String       @id @default(cuid())
  memberships Membership[]
}

model Team {
  id          String       @id @default(cuid())
  memberships Membership[]
}

model Membership {
  id       String   @id @default(cuid())
  role     String   @default("member")
  joinedAt DateTime @default(now())
  
  user     User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId   String
  
  team     Team     @relation(fields: [teamId], references: [id], onDelete: Cascade)
  teamId   String
  
  @@unique([userId, teamId])
  @@index([userId])
  @@index([teamId])
}
```

## Self-Relation (Comments/Replies)

```prisma
model Comment {
  id       String    @id @default(cuid())
  content  String
  
  parent   Comment?  @relation("CommentReplies", fields: [parentId], references: [id], onDelete: Cascade)
  parentId String?
  replies  Comment[] @relation("CommentReplies")
  
  author   User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  authorId String

  @@index([parentId])
  @@index([authorId])
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
      create: { bio: 'Hello' },
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

// Pagination
const posts = await prisma.post.findMany({
  skip: (page - 1) * limit,
  take: limit,
  orderBy: { createdAt: 'desc' },
});

// Search
const users = await prisma.user.findMany({
  where: {
    OR: [
      { name: { contains: search, mode: 'insensitive' } },
      { email: { contains: search, mode: 'insensitive' } },
    ],
  },
});

// Update nested
const updated = await prisma.user.update({
  where: { id },
  data: {
    profile: {
      upsert: {
        create: { bio: 'New' },
        update: { bio: 'Updated' },
      },
    },
  },
});

// Transaction
const [user, post] = await prisma.$transaction([
  prisma.user.create({ data: { ... } }),
  prisma.post.create({ data: { ... } }),
]);
```

## Field Types

| Type | Prisma | PostgreSQL |
|------|--------|------------|
| String | `String` | `text` |
| Integer | `Int` | `integer` |
| Float | `Float` | `double precision` |
| Boolean | `Boolean` | `boolean` |
| DateTime | `DateTime` | `timestamp` |
| JSON | `Json` | `jsonb` |
| Optional | `String?` | nullable |
| Array | `String[]` | `text[]` |
