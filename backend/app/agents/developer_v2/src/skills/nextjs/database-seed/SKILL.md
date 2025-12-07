---
name: database-seed
description: Create Prisma seed scripts with realistic sample data. Use when populating database with test/demo data for development.
---

This skill guides creation of Prisma seed scripts for Next.js applications.

## File Location

- **Seed file**: `prisma/seed.ts`
- **Run command**: `bunx tsx prisma/seed.ts` or `bunx prisma db seed`

## Basic Structure

```typescript
// prisma/seed.ts
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding database...');
  
  // Seed data here
  
  console.log('✅ Seeding completed!');
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

## Seeding Patterns

### Clear and Reseed (Development)

```typescript
async function main() {
  // Clear in reverse dependency order
  await prisma.orderItem.deleteMany();
  await prisma.order.deleteMany();
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();
  
  // Seed in dependency order
  const categories = await seedCategories();
  const books = await seedBooks(categories);
  await seedOrders(books);
}
```

### Upsert Pattern (Safe for Production)

```typescript
async function seedCategories() {
  const categories = [
    { id: 'cat-1', name: 'Fiction', slug: 'fiction' },
    { id: 'cat-2', name: 'Non-Fiction', slug: 'non-fiction' },
  ];
  
  for (const cat of categories) {
    await prisma.category.upsert({
      where: { id: cat.id },
      update: cat,
      create: cat,
    });
  }
}
```

### Bulk Create with createMany

```typescript
async function seedBooks(categoryIds: string[]) {
  const books = Array.from({ length: 50 }, (_, i) => ({
    title: `Book Title ${i + 1}`,
    author: `Author ${(i % 10) + 1}`,
    price: Math.round((9.99 + Math.random() * 40) * 100) / 100,
    stock: Math.floor(Math.random() * 100),
    categoryId: categoryIds[i % categoryIds.length],
  }));
  
  await prisma.book.createMany({ data: books });
  console.log(`📚 Created ${books.length} books`);
}
```

## Realistic Data Examples

### Books Store

```typescript
const books = [
  {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    price: 14.99,
    stock: 45,
    coverUrl: '/covers/gatsby.jpg',
    description: 'A story of decadence and excess...',
  },
  {
    title: 'To Kill a Mockingbird',
    author: 'Harper Lee',
    price: 12.99,
    stock: 32,
    coverUrl: '/covers/mockingbird.jpg',
    description: 'The story of racial injustice...',
  },
  {
    title: '1984',
    author: 'George Orwell',
    price: 11.99,
    stock: 28,
    coverUrl: '/covers/1984.jpg',
    description: 'A dystopian social science fiction...',
  },
];
```

### Categories with Hierarchy

```typescript
const categories = [
  { name: 'Fiction', slug: 'fiction', parentId: null },
  { name: 'Non-Fiction', slug: 'non-fiction', parentId: null },
  { name: 'Science Fiction', slug: 'sci-fi', parentId: 'fiction-id' },
  { name: 'Mystery', slug: 'mystery', parentId: 'fiction-id' },
  { name: 'Biography', slug: 'biography', parentId: 'non-fiction-id' },
];
```

### Users with Roles

```typescript
import bcrypt from 'bcryptjs';

const users = [
  {
    email: 'admin@example.com',
    username: 'admin',
    password: await bcrypt.hash('admin123', 10),
    role: 'ADMIN',
  },
  {
    email: 'user@example.com',
    username: 'testuser',
    password: await bcrypt.hash('user123', 10),
    role: 'USER',
  },
];
```

## Related Records

```typescript
async function seedOrders() {
  const users = await prisma.user.findMany();
  const books = await prisma.book.findMany();
  
  for (const user of users) {
    // Create 1-3 orders per user
    const orderCount = Math.floor(Math.random() * 3) + 1;
    
    for (let i = 0; i < orderCount; i++) {
      const order = await prisma.order.create({
        data: {
          userId: user.id,
          status: 'DELIVERED',
          total: 0,
          items: {
            create: [
              {
                bookId: books[Math.floor(Math.random() * books.length)].id,
                quantity: Math.floor(Math.random() * 3) + 1,
                price: books[0].price,
              },
            ],
          },
        },
      });
    }
  }
}
```

## Best Practices

1. **Use deterministic IDs** for upsert operations
2. **Seed in dependency order** (categories before books)
3. **Clear in reverse order** to avoid FK violations
4. **Log progress** for debugging
5. **Use realistic data** that covers edge cases
6. **Include various states** (active/inactive, different statuses)
7. **Match schema exactly** - check field names and types
