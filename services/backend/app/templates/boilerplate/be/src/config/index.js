/**
 * Application configuration
 * Centralized configuration management with environment variables
 */

require('dotenv').config();

const config = {
  // Basic app settings
  NODE_ENV: process.env.NODE_ENV || 'development',
  PORT: parseInt(process.env.PORT, 10) || 3000,

  // Security
  JWT_SECRET: process.env.JWT_SECRET,
  JWT_EXPIRE: process.env.JWT_EXPIRE || '1h',
  JWT_REFRESH_EXPIRE: process.env.JWT_REFRESH_EXPIRE || '7d',
  BCRYPT_ROUNDS: parseInt(process.env.BCRYPT_ROUNDS, 10) || 12,

  // Database
  MONGODB_URI: process.env.MONGODB_URI,

  // Redis
  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',

  // CORS
  CORS_ORIGINS: process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map(origin => origin.trim())
    : ['http://localhost:3000', 'http://localhost:8080'],

  // File uploads
  MAX_FILE_SIZE: parseInt(process.env.MAX_FILE_SIZE, 10) || 10 * 1024 * 1024, // 10MB
  UPLOAD_DIR: process.env.UPLOAD_DIR || 'uploads',
}

module.exports = config
