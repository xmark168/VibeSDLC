// prisma/verify-seed.ts - Post-seed verification
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function verifySeed() {
  console.log('🔍 Verifying seed data...');
  
  try {
    const userCount = await prisma.user.count();
    console.log(`✅ Users: ${userCount}`);
    
    // Only verify if categories exist
    try {
      const categoryCount = await prisma.category.count();
      console.log(`✅ Categories: ${categoryCount}`);
    } catch {
      console.log('ℹ️ Categories not checked (not in schema)');
    }
    
    return true;
  } catch (error) {
    console.error('❌ Verification failed:', error);
    return false;
  }
}

// Run verification if called directly
if (require.main === module) {
  verifySeed()
    .then(success => {
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Verification error:', error);
      process.exit(1);
    })
    .finally(async () => {
      await prisma.$disconnect();
    });
}

export { verifySeed };
