---
name: database-seed
description: Create Prisma seed scripts with sample data. Use when populating database with test data.
---

## File: `prisma/seed.ts`

```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding...');
  
  // Clear existing (reverse dependency order)
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();
  
  // Seed categories first
  const categories = await prisma.category.createManyAndReturn({
    data: [
      { name: 'Fiction', slug: 'fiction' },
      { name: 'Science', slug: 'science' },
    ]
  });
  
  // Seed books with category references
  await prisma.book.createMany({
    data: Array.from({ length: 5 }, (_, i) => ({
      title: `Book ${i + 1}`,
      author: `Author ${i + 1}`,
      price: 9.99 + i * 5,
      coverImage: `https://picsum.photos/seed/book${i}/200/300`,
      categoryId: categories[i % categories.length].id,
    }))
  });
  
  console.log('✅ Done!');
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
```

## Rules

1. **Clear first**: `deleteMany()` in reverse dependency order
2. **Use createMany**: Fastest for bulk inserts
3. **Simple data**: `Book ${i}`, `Author ${i}` - don't overthink
4. **Images**: `https://picsum.photos/seed/{unique}/width/height`
5. **5-10 records**: Enough for testing, not too slow

## NEVER
- Complex nested creates (slow)
- Realistic book titles/descriptions (wastes tokens)
- More than 10 records per model
