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
  JWT_SECRET: process.env.JWT_SECRET || 'your-super-secret-jwt-key',
  JWT_EXPIRE: process.env.JWT_EXPIRE || '1h',
  JWT_REFRESH_EXPIRE: process.env.JWT_REFRESH_EXPIRE || '7d',
  BCRYPT_ROUNDS: parseInt(process.env.BCRYPT_ROUNDS, 10) || 12,

  // Database
  MONGODB_URI: process.env.MONGODB_URI || 'mongodb://localhost:27017/express_basic',

  // Redis
  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',

  // CORS
  CORS_ORIGINS: process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map(origin => origin.trim())
    : ['http://localhost:3000', 'http://localhost:8080'],

  // File uploads
  MAX_FILE_SIZE: parseInt(process.env.MAX_FILE_SIZE, 10) || 10 * 1024 * 1024, // 10MB
  UPLOAD_DIR: process.env.UPLOAD_DIR || 'uploads',

  // Email configuration
  SMTP_HOST: process.env.SMTP_HOST,
  SMTP_PORT: parseInt(process.env.SMTP_PORT, 10) || 587,
  SMTP_USER: process.env.SMTP_USER,
  SMTP_PASS: process.env.SMTP_PASS,
  SMTP_FROM: process.env.SMTP_FROM,

  // External APIs
  EXTERNAL_API_KEY: process.env.EXTERNAL_API_KEY,
  EXTERNAL_API_URL: process.env.EXTERNAL_API_URL,

  // Logging
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',

  // Rate limiting
  RATE_LIMIT_WINDOW: parseInt(process.env.RATE_LIMIT_WINDOW, 10) || 15 * 60 * 1000, // 15 minutes
  RATE_LIMIT_MAX: parseInt(process.env.RATE_LIMIT_MAX, 10) || 100,

  // Monitoring
  SENTRY_DSN: process.env.SENTRY_DSN,
};

// Validation
const requiredEnvVars = ['JWT_SECRET', 'MONGODB_URI'];

// Always require MONGODB_URI for safety
// (If you want to restrict to production only, revert this change)

const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
  const AppError = require('../utils/AppError');
  throw new AppError(`Missing required environment variables: ${missingEnvVars.join(', ')}`, 500);
}

module.exports = config;
