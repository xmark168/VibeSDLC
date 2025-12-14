---
name: database-seed
description: Create idempotent Prisma seed scripts. CRITICAL - Must use upsert for @unique fields to avoid "Unique constraint failed" errors on re-run.
---

## 🚨🚨🚨 ABSOLUTE RULES - VIOLATION CAUSES SEED FAILURE 🚨🚨🚨

### ❌ FORBIDDEN: createMany/createManyAndReturn on @unique fields
```typescript
// ❌ WILL FAIL with "Unique constraint failed" on re-run
await prisma.category.createManyAndReturn({ data: [...] })
await prisma.author.createMany({ data: [...] })
await prisma.user.createMany({ data: [...] })
```

### ✅ REQUIRED: ALWAYS use upsert for ANY table with @unique
```typescript
// ✅ CORRECT - Safe to run multiple times
const items = await Promise.all(
  uniqueValues.map((value) =>
    prisma.model.upsert({
      where: { uniqueField: value },
      update: {},  // Skip if exists
      create: { uniqueField: value, ...otherFields },
    })
  )
);
```

## BEFORE WRITING SEED: Check schema.prisma for @unique

```prisma
model Category {
  name String @unique  // ← HAS @unique → MUST use upsert
}
model Author {
  email String @unique  // ← HAS @unique → MUST use upsert
}
model Book {
  // No @unique field → Can use deleteMany + createMany
}
```

## Template (COPY EXACTLY - DO NOT MODIFY PATTERN)

```typescript
// prisma/seed.ts
import { PrismaClient } from '@prisma/client';
import { faker } from '@faker-js/faker';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting seed...');

  // ============================================================
  // STEP 1: Tables with @unique → UPSERT (idempotent)
  // ============================================================
  
  // Categories (name is @unique)
  const categoryNames = ['Fiction', 'Non-Fiction', 'Science', 'History', 'Technology'];
  const categories = await Promise.all(
    categoryNames.map((name) =>
      prisma.category.upsert({
        where: { name },
        update: {},
        create: { name, slug: name.toLowerCase().replace(/\s+/g, '-') },
      })
    )
  );
  console.log(`✅ Upserted ${categories.length} categories`);

  // Authors (email is @unique)
  const authorData = [
    { email: 'john@example.com', name: 'John Doe' },
    { email: 'jane@example.com', name: 'Jane Smith' },
    { email: 'bob@example.com', name: 'Bob Wilson' },
  ];
  const authors = await Promise.all(
    authorData.map((author) =>
      prisma.author.upsert({
        where: { email: author.email },
        update: {},
        create: { ...author, bio: faker.lorem.paragraph() },
      })
    )
  );
  console.log(`✅ Upserted ${authors.length} authors`);

  // ============================================================
  // STEP 2: Tables WITHOUT @unique → deleteMany + createMany
  // ============================================================
  
  await prisma.book.deleteMany();
  await prisma.book.createMany({
    data: Array.from({ length: 5 }, () => ({
      title: faker.commerce.productName(),
      price: faker.number.float({ min: 9.99, max: 49.99, fractionDigits: 2 }),
      coverImage: `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600`,
      categoryId: faker.helpers.arrayElement(categories).id,
      authorId: faker.helpers.arrayElement(authors).id,
    })),
  });
  console.log('✅ Created 5 books');

  console.log('🌱 Seed completed!');
}

main()
  .catch((e) => { console.error('❌ Seed failed:', e); process.exit(1); })
  .finally(() => prisma.$disconnect());
```

## Decision Tree: Which method to use?

```
Does the table have @unique field?
├── YES → Use Promise.all + upsert
│         where: { uniqueField: value }
│         update: {}
│         create: { ...data }
│
└── NO → Use deleteMany + createMany
         await prisma.model.deleteMany()
         await prisma.model.createMany({ data: [...] })
```

## Faker v9+ Cheatsheet

| Field Type | Faker Method |
|------------|-------------|
| Full Name | `faker.person.fullName()` |
| Email | `faker.internet.email()` |
| Username | `faker.internet.username()` |
| Title/Name | `faker.commerce.productName()` |
| Description | `faker.lorem.sentence()` |
| Paragraph | `faker.lorem.paragraph()` |
| Price | `faker.number.float({ min: 10, max: 100, fractionDigits: 2 })` |
| Integer | `faker.number.int({ min: 1, max: 100 })` |
| Image | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600` `` |
| UUID | `faker.string.uuid()` |
| Date | `faker.date.past()` |
| Boolean | `faker.datatype.boolean()` |
| Pick from array | `faker.helpers.arrayElement(array)` |

## ❌ DEPRECATED (v8) → ✅ USE (v9+)

| ❌ Old | ✅ New |
|--------|--------|
| `faker.name.fullName()` | `faker.person.fullName()` |
| `faker.internet.userName()` | `faker.internet.username()` |
| `faker.datatype.uuid()` | `faker.string.uuid()` |

## Rules Summary

1. **Check schema for @unique** before writing seed
2. **UPSERT** for tables with @unique fields
3. **deleteMany + createMany** for tables without @unique
4. **MAX 5 records** per model
5. **Predefined arrays** for unique values (not faker)
6. **faker** for non-unique text fields

## 🚫 NEVER (Will cause seed failure)

- `createMany` on tables with @unique fields
- `createManyAndReturn` on tables with @unique fields
- `faker.commerce.department()` for unique names (only ~10 values)
- Running seed without checking schema for @unique first
