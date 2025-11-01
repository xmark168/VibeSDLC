const mongoose = require('mongoose');
const User = require('../../models/User');

/**
 * Migration: Ensure User collection exists and is up to date
 * Add more migration logic as needed for future schemas
 */
async function migrate() {
  try {
    // Connect to MongoDB
    await mongoose.connect(process.env.MONGODB_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });

    // Ensure User collection is created (Mongoose does this automatically)
    await User.init();

    // Add more migration steps here as needed
    console.log('Migration completed: User collection ensured.');
    await mongoose.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('Migration failed:', err);
    process.exit(1);
  }
}

if (require.main === module) {
  migrate();
}

module.exports = migrate;
