const AppError = require('./AppError');
const logger = require('../utils/logger');

/**
 * Centralized Express error handling middleware.
 * Catches errors and formats response.
 */
function errorHandler(err, req, res, next) {
  // Log the error
  logger.error(err);

  // If error is an instance of AppError, use its properties
  if (err instanceof AppError) {
    return res.status(err.statusCode || 500).json({
      error: err.name || 'AppError',
      message: err.message,
      statusCode: err.statusCode || 500,
      details: err.details || undefined,
    });
  }

  // Handle validation errors from Joi
  if (err.isJoi) {
    return res.status(400).json({
      error: 'ValidationError',
      message: err.details?.map(d => d.message).join(', ') || err.message,
      statusCode: 400,
    });
  }

  // Fallback for other errors
  return res.status(500).json({
    error: err.name || 'InternalServerError',
    message: err.message || 'An unexpected error occurred',
    statusCode: 500,
  });
}

module.exports = errorHandler;
