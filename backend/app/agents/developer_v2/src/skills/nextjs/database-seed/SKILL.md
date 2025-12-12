---
name: database-seed
description: Create Prisma seed scripts with faker-generated data. Use when populating database with test data.
---

## ⚠️ CRITICAL - Use faker, NOT manual data

```typescript
import { faker } from '@faker-js/faker';

// ✅ CORRECT - generate with faker
Array.from({ length: 5 }, () => ({
  name: faker.commerce.productName(),
  price: faker.number.float({ min: 10, max: 100 }),
}))

// ❌ WRONG - manual data (wastes tokens!)
[
  { name: 'Book 1', price: 10 },
  { name: 'Book 2', price: 20 },
]
```

## Template

```typescript
// prisma/seed.ts
import { PrismaClient } from '@prisma/client';
import { faker } from '@faker-js/faker';

const prisma = new PrismaClient();

async function main() {
  // Clear existing (reverse dependency order)
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();
  
  // Seed categories - USE PREDEFINED NAMES for unique constraints!
  // ⚠️ NEVER use faker.commerce.department() for unique fields (only ~10 values, causes duplicates)
  const categoryNames = ['Fiction', 'Non-Fiction', 'Science', 'History', 'Technology'];
  const categories = await prisma.category.createManyAndReturn({
    data: categoryNames.map((name) => ({
      name,
      slug: name.toLowerCase().replace(/\s+/g, '-'),
    }))
  });
  
  // Seed books with relations
  await prisma.book.createMany({
    data: Array.from({ length: 5 }, () => ({
      title: faker.commerce.productName(),
      author: faker.person.fullName(),
      price: faker.number.float({ min: 9.99, max: 49.99, fractionDigits: 2 }),
      coverImage: `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600`,
      categoryId: faker.helpers.arrayElement(categories).id,
    }))
  });
  
  console.log('✅ Seeded!');
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
```

## Faker v9+ Cheatsheet (LATEST API)

| Field Type | Faker Method (v9+) |
|------------|-------------------|
| Full Name | `faker.person.fullName()` |
| First Name | `faker.person.firstName()` |
| Last Name | `faker.person.lastName()` |
| Username | `faker.internet.username()` |
| Email | `faker.internet.email()` |
| Password | `faker.internet.password()` |
| Title | `faker.commerce.productName()` |
| Description | `faker.lorem.sentence()` |
| Paragraph | `faker.lorem.paragraph()` |
| Price | `faker.number.float({ min: 10, max: 100, fractionDigits: 2 })` |
| Integer | `faker.number.int({ min: 1, max: 100 })` |
| Image (cover) | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600` `` |
| Image (banner) | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/1200/600` `` |
| Image (card) | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/800/600` `` |
| Image (thumb) | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/300/300` `` |
| Avatar | `faker.image.avatar()` |
| Slug | `faker.helpers.slugify(name).toLowerCase()` |
| UUID | `faker.string.uuid()` |
| Date Past | `faker.date.past()` |
| Date Recent | `faker.date.recent()` |
| Boolean | `faker.datatype.boolean()` |
| Pick from array | `faker.helpers.arrayElement(array)` |
| ISBN | `faker.commerce.isbn()` |
| Phone | `faker.phone.number()` |

## ⚠️ DEPRECATED - Do NOT use

| ❌ Deprecated (v8) | ✅ Use Instead (v9+) |
|-------------------|---------------------|
| `faker.internet.userName()` | `faker.internet.username()` |
| `faker.name.firstName()` | `faker.person.firstName()` |
| `faker.name.lastName()` | `faker.person.lastName()` |
| `faker.name.fullName()` | `faker.person.fullName()` |
| `faker.datatype.uuid()` | `faker.string.uuid()` |
| `faker.random.alphaNumeric()` | `faker.string.alphanumeric()` |
| `faker.random.word()` | `faker.lorem.word()` |
| `faker.image.imageUrl()` | `faker.image.url()` |
| `faker.image.urlPicsumPhotos()` | `` `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/W/H` `` |

## Rules

1. **MAX 5 records** per model
2. **Use createMany** for bulk inserts
3. **Clear first** in reverse dependency order
4. **faker for ALL text** - no manual strings
5. **Unique fields** - Use predefined arrays, NOT faker (faker has limited values → duplicates)

## ⚠️ Unique Constraint Warning

For fields with `@unique` constraint, **DO NOT use faker** - it has limited values:

```typescript
// ❌ WRONG - faker.commerce.department() only has ~10 values → duplicates!
const categories = await prisma.category.createManyAndReturn({
  data: Array.from({ length: 5 }, () => ({
    name: faker.commerce.department(),  // Will fail with unique constraint
  }))
});

// ✅ CORRECT - predefined unique values
const categoryNames = ['Fiction', 'Non-Fiction', 'Science', 'History', 'Technology'];
const categories = await prisma.category.createManyAndReturn({
  data: categoryNames.map((name) => ({
    name,
    slug: name.toLowerCase().replace(/\s+/g, '-'),
  }))
});
```

## NEVER
- Manual data arrays (except for unique constraint fields)
- More than 5 records per model
- Individual create() calls
- Complex nested creates
- `faker.commerce.department()` for unique name fields
