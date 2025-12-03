import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

// Lazy initialization to avoid errors when Prisma client not generated
let prismaInstance: PrismaClient | null = null;

export const prisma = globalForPrisma.prisma ?? (() => {
  if (!prismaInstance) {
    prismaInstance = new PrismaClient({
      datasourceUrl: process.env.DATABASE_URL,
      log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
    });
  }
  return prismaInstance;
})();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

export default prisma;
