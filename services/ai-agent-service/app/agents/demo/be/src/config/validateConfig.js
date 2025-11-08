const Joi = require('joi');
const dotenv = require('dotenv');
const logger = require('../utils/logger');

dotenv.config();

const envSchema = Joi.object({
  NODE_ENV: Joi.string().valid('development', 'production', 'test').default('development'),
  PORT: Joi.number().integer().min(1).max(65535).default(3000),
  JWT_SECRET: Joi.string().min(10).required(),
  JWT_EXPIRE: Joi.string().default('1h'),
  JWT_REFRESH_EXPIRE: Joi.string().default('7d'),
  BCRYPT_ROUNDS: Joi.number().integer().min(4).max(20).default(12),
  MONGODB_URI: Joi.string().uri().required(),
  REDIS_URL: Joi.string().uri().default('redis://localhost:6379'),
  CORS_ORIGINS: Joi.string().default('http://localhost:3000,http://localhost:8080'),
  MAX_FILE_SIZE: Joi.number().integer().min(1024).default(10 * 1024 * 1024),
  UPLOAD_DIR: Joi.string().default('uploads'),
  EMAIL_SERVICE: Joi.string().optional(),
  EMAIL_USER: Joi.string().optional(),
  EMAIL_PASS: Joi.string().optional(),
  EMAIL_FROM: Joi.string().optional()
}).unknown();

const { value: envVars, error } = envSchema.validate(process.env, { abortEarly: false });

if (error) {
  logger.error('Config validation error:', error.details.map(e => e.message).join('; '));
  throw new Error(`Config validation error: ${error.details.map(e => e.message).join('; ')}`);
}

module.exports = envVars;
