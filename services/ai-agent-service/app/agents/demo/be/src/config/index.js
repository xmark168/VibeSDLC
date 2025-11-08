/**
 * Application configuration
 * Centralized configuration management with environment variables
 */

const envVars = require('./validateConfig');

const config = {
  // Basic app settings
  NODE_ENV: envVars.NODE_ENV,
  PORT: envVars.PORT,

  // Security
  JWT_SECRET: envVars.JWT_SECRET,
  JWT_EXPIRE: envVars.JWT_EXPIRE,
  JWT_REFRESH_EXPIRE: envVars.JWT_REFRESH_EXPIRE,
  BCRYPT_ROUNDS: envVars.BCRYPT_ROUNDS,

  // Database
  MONGODB_URI: envVars.MONGODB_URI,

  // Redis
  REDIS_URL: envVars.REDIS_URL,

  // CORS
  CORS_ORIGINS: envVars.CORS_ORIGINS.split(',').map(origin => origin.trim()),

  // File uploads
  MAX_FILE_SIZE: envVars.MAX_FILE_SIZE,
  UPLOAD_DIR: envVars.UPLOAD_DIR,

  // Email (optional)
  EMAIL_SERVICE: envVars.EMAIL_SERVICE,
  EMAIL_USER: envVars.EMAIL_USER,
  EMAIL_PASS: envVars.EMAIL_PASS,
  EMAIL_FROM: envVars.EMAIL_FROM
};

module.exports = config;
