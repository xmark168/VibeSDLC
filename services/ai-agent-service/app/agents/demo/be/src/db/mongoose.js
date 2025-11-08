const mongoose = require('mongoose');
const config = require('../config');
const logger = require('../utils/logger');
const AppError = require('../middleware/AppError');

const connectDB = async () => {
  try {
    await mongoose.connect(config.MONGODB_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
    logger.info('MongoDB connected');
  } catch (error) {
    logger.error('MongoDB connection error:', error);
    // Optionally, you can throw an AppError for further handling
    // throw new AppError('Failed to connect to MongoDB', 500);
    process.exit(1);
  }
};

module.exports = connectDB;
