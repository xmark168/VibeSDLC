import { PrismaClient } from '@prisma/client';
import { faker } from '@faker-js/faker';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting seed...');

  // Clear existing data (reverse dependency order)
  await prisma.orderItem.deleteMany();
  await prisma.order.deleteMany();
  await prisma.cartItem.deleteMany();
  await prisma.cart.deleteMany();
  await prisma.review.deleteMany();
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();
  await prisma.user.deleteMany();

  console.log('🗑️  Cleared existing data');

  // Seed Categories
  const categories = await prisma.category.createManyAndReturn({
    data: Array.from({ length: 5 }, () => {
      const name = faker.commerce.department();
      return {
        name,
        slug: faker.helpers.slugify(name).toLowerCase(),
        description: faker.lorem.sentence(),
      };
    }),
  });

  console.log(`✅ Created ${categories.length} categories`);

  // Seed Users
  const users = await prisma.user.createManyAndReturn({
    data: Array.from({ length: 5 }, () => ({
      email: faker.internet.email(),
      name: faker.person.fullName(),
      password: faker.internet.password(),
    })),
  });

  console.log(`✅ Created ${users.length} users`);

  // Seed Books
  const books = await prisma.book.createManyAndReturn({
    data: Array.from({ length: 5 }, () => ({
      title: faker.commerce.productName(),
      author: faker.person.fullName(),
      description: faker.lorem.paragraph(),
      price: faker.number.float({ min: 9.99, max: 49.99, fractionDigits: 2 }),
      coverImage: `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600`,
      isbn: faker.commerce.isbn(),
      stock: faker.number.int({ min: 0, max: 100 }),
      categoryId: faker.helpers.arrayElement(categories).id,
      isFeatured: faker.datatype.boolean(),
      isBestseller: faker.datatype.boolean(),
    })),
  });

  console.log(`✅ Created ${books.length} books`);

  // Seed Reviews
  await prisma.review.createMany({
    data: Array.from({ length: 5 }, () => ({
      rating: faker.number.int({ min: 1, max: 5 }),
      comment: faker.lorem.paragraph(),
      userId: faker.helpers.arrayElement(users).id,
      bookId: faker.helpers.arrayElement(books).id,
    })),
  });

  console.log('✅ Created 5 reviews');

  // Seed Carts
  const carts = await prisma.cart.createManyAndReturn({
    data: Array.from({ length: 3 }, () => ({
      userId: faker.helpers.arrayElement(users).id,
    })),
  });

  console.log(`✅ Created ${carts.length} carts`);

  // Seed Cart Items
  await prisma.cartItem.createMany({
    data: Array.from({ length: 5 }, () => ({
      quantity: faker.number.int({ min: 1, max: 5 }),
      cartId: faker.helpers.arrayElement(carts).id,
      bookId: faker.helpers.arrayElement(books).id,
    })),
  });

  console.log('✅ Created 5 cart items');

  // Seed Orders
  const orders = await prisma.order.createManyAndReturn({
    data: Array.from({ length: 5 }, () => ({
      total: faker.number.float({ min: 20, max: 200, fractionDigits: 2 }),
      status: faker.helpers.arrayElement(['PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED']),
      userId: faker.helpers.arrayElement(users).id,
    })),
  });

  console.log(`✅ Created ${orders.length} orders`);

  // Seed Order Items
  await prisma.orderItem.createMany({
    data: Array.from({ length: 5 }, () => ({
      quantity: faker.number.int({ min: 1, max: 3 }),
      price: faker.number.float({ min: 9.99, max: 49.99, fractionDigits: 2 }),
      orderId: faker.helpers.arrayElement(orders).id,
      bookId: faker.helpers.arrayElement(books).id,
    })),
  });

  console.log('✅ Created 5 order items');

  console.log('🎉 Seed completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
