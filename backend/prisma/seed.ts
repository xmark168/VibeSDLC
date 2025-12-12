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
  await prisma.book.deleteMany();
  await prisma.category.deleteMany();
  await prisma.user.deleteMany();

  console.log('🗑️  Cleared existing data');

  // Seed Categories
  const categories = await prisma.category.createManyAndReturn({
    data: [
      {
        name: 'Fiction',
        slug: 'fiction',
        description: faker.lorem.sentence(),
      },
      {
        name: 'Non-Fiction',
        slug: 'non-fiction',
        description: faker.lorem.sentence(),
      },
      {
        name: 'Science',
        slug: 'science',
        description: faker.lorem.sentence(),
      },
      {
        name: 'Technology',
        slug: 'technology',
        description: faker.lorem.sentence(),
      },
      {
        name: 'Business',
        slug: 'business',
        description: faker.lorem.sentence(),
      },
    ],
  });

  console.log(`✅ Seeded ${categories.length} categories`);

  // Seed Books
  const books = await prisma.book.createManyAndReturn({
    data: Array.from({ length: 5 }, () => {
      const title = faker.commerce.productName();
      return {
        title,
        slug: faker.helpers.slugify(title).toLowerCase(),
        author: faker.person.fullName(),
        description: faker.lorem.paragraph(),
        price: faker.number.float({ min: 9.99, max: 49.99, fractionDigits: 2 }),
        coverImage: `https://picsum.photos/seed/${faker.string.alphanumeric(8)}/400/600`,
        isbn: faker.commerce.isbn(),
        publishedDate: faker.date.past(),
        stock: faker.number.int({ min: 10, max: 100 }),
        categoryId: faker.helpers.arrayElement(categories).id,
      };
    }),
  });

  console.log(`✅ Seeded ${books.length} books`);

  // Seed Users
  const users = await prisma.user.createManyAndReturn({
    data: Array.from({ length: 3 }, () => ({
      email: faker.internet.email(),
      name: faker.person.fullName(),
      password: faker.internet.password(),
    })),
  });

  console.log(`✅ Seeded ${users.length} users`);

  // Seed Carts with CartItems
  for (const user of users) {
    const cart = await prisma.cart.create({
      data: {
        userId: user.id,
      },
    });

    await prisma.cartItem.createMany({
      data: Array.from({ length: faker.number.int({ min: 1, max: 3 }) }, () => ({
        cartId: cart.id,
        bookId: faker.helpers.arrayElement(books).id,
        quantity: faker.number.int({ min: 1, max: 3 }),
      })),
    });
  }

  console.log('✅ Seeded carts with items');

  // Seed Orders with OrderItems
  for (const user of users.slice(0, 2)) {
    const order = await prisma.order.create({
      data: {
        userId: user.id,
        total: faker.number.float({ min: 50, max: 200, fractionDigits: 2 }),
        status: faker.helpers.arrayElement(['PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED']),
      },
    });

    await prisma.orderItem.createMany({
      data: Array.from({ length: faker.number.int({ min: 1, max: 3 }) }, () => {
        const book = faker.helpers.arrayElement(books);
        const quantity = faker.number.int({ min: 1, max: 3 });
        return {
          orderId: order.id,
          bookId: book.id,
          quantity,
          price: book.price,
        };
      }),
    });
  }

  console.log('✅ Seeded orders with items');

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
