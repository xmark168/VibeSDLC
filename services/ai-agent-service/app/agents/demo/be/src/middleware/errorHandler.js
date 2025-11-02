const AppError = require('../utils/AppError');

const logger = require('../utils/logger');

function errorHandler(err, req, res, next) {
  // If error is not an instance of AppError, convert it
  if (!(err instanceof AppError)) {
    err = new AppError(err.message || 'Internal Server Error', err.statusCode || 500);
  }

  // Log error
  logger.error(err);

  // Format error response
  res.status(err.statusCode || 500).json({
    status: 'error',
    message: err.message || 'Internal Server Error',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
}

module.exports = errorHandler;
